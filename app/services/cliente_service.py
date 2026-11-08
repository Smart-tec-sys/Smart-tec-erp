import re

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.cliente import ClienteDB
from app.schemas.cliente import ClienteCreate, ClienteReclassificarRevenda, ClienteUpdate
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant
from app.services.representante_service import (
    PARCEIRO_RESPONSE_FIELDS,
    _limite_credito,
    _normalizar_documento,
    _normalizar_textos,
    _parceiro_response,
    _percentual_parceiro,
    _validar_consistencia_fiscal,
    _validar_vendedor_empresa,
)


def _validar_vinculo_comercial(
    db: Session,
    dados: dict,
    tenant: TenantContext,
):
    empresa_id = require_tenant(tenant)

    parceiro_id = dados.get("parceiro_id")
    representante_id = dados.get("representante_id")

    if parceiro_id and representante_id:
        raise ValueError(
            "Cliente não pode estar vinculado a parceiro e representante ao mesmo tempo."
        )

    if parceiro_id:
        parceiro = db.execute(
            text("""
                SELECT id
                FROM parceiros_comerciais
                WHERE id = :id
                  AND empresa_id = :empresa_id
                  AND ativo = TRUE
            """),
            {
                "id": parceiro_id,
                "empresa_id": empresa_id,
            },
        ).first()

        if not parceiro:
            raise ValueError(
                "Parceiro comercial inválido para esta empresa."
            )

    if representante_id:
        representante = db.execute(
            text("""
                SELECT id
                FROM representantes
                WHERE id = :id
                  AND empresa_id = :empresa_id
                  AND ativo = TRUE
            """),
            {
                "id": representante_id,
                "empresa_id": empresa_id,
            },
        ).first()

        if not representante:
            raise ValueError(
                "Representante inválido para esta empresa."
            )

def get_all(db: Session, tenant: TenantContext):
    """Busca todos os clientes cadastrados no banco de dados."""
    empresa_id = require_tenant(tenant)
    return (
        db.query(ClienteDB)
        .filter(
            ClienteDB.empresa_id == empresa_id,
            text("""
                NOT EXISTS (
                    SELECT 1
                    FROM parceiros_comerciais pc
                    WHERE pc.empresa_id = clientes.empresa_id
                      AND pc.cliente_origem_id = clientes.id
                )
            """),
        )
        .order_by(ClienteDB.id.desc())
        .all()
    )


def get_by_id(db: Session, cliente_id: int, tenant: TenantContext):
    """Busca um cliente específico pelo ID."""
    try:
        return db.query(ClienteDB).filter(
            ClienteDB.id == cliente_id,
            ClienteDB.empresa_id == require_tenant(tenant),
        ).first()
    except Exception as e:
        print(f"Erro ao buscar cliente por ID no service: {e}")
        return None


def create(db: Session, data: ClienteCreate, tenant: TenantContext):
    """Cria um novo cliente."""
    try:
        dados_cliente = data.dict()

        _validar_vinculo_comercial(
            db,
            dados_cliente,
            tenant,
        )
        novo_cliente = ClienteDB(**dados_cliente, empresa_id=require_tenant(tenant))

        db.add(novo_cliente)
        db.commit()
        db.refresh(novo_cliente)

        return novo_cliente

    except Exception as e:
        db.rollback()
        print(f"Erro crítico dentro de cliente_service.create: {e}")
        raise e


def update(db: Session, cliente_id: int, data: ClienteUpdate, tenant: TenantContext):
    """Atualiza um cliente existente."""
    try:
        cliente = get_by_id(db, cliente_id, tenant)

        if not cliente:
            return None

        dados_cliente = data.dict()
        dados_cliente.pop("empresa_id", None)

        _validar_vinculo_comercial(
            db,
            dados_cliente,
            tenant,
        )
        for campo, valor in dados_cliente.items():
            setattr(cliente, campo, valor)

        db.commit()
        db.refresh(cliente)

        return cliente

    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar cliente no service: {e}")
        raise e


def delete(db: Session, cliente_id: int, tenant: TenantContext):
    """Remove um cliente pelo ID."""
    try:
        cliente = get_by_id(db, cliente_id, tenant)

        if cliente:
            vinculo_revenda = db.execute(
                text("""
                    SELECT id
                    FROM parceiros_comerciais
                    WHERE empresa_id = :empresa_id
                      AND cliente_origem_id = :cliente_id
                """),
                {
                    "empresa_id": require_tenant(tenant),
                    "cliente_id": cliente_id,
                },
            ).first()
            if vinculo_revenda:
                raise ValueError(
                    "Cliente reclassificado como revenda não pode ser excluído."
                )
            db.delete(cliente)
            db.commit()
            return cliente

        return None

    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar cliente no service: {e}")
        return None


_PARCEIRO_FIELDS = tuple(
    field for field in PARCEIRO_RESPONSE_FIELDS
    if field not in {"id", "empresa_id", "criado_em", "atualizado_em"}
)


def _valor_cnpj(valor):
    documento = _normalizar_documento(valor)
    if documento and re.fullmatch(r"[0-9A-Z]{12}\d{2}", documento):
        return documento
    return None


def _dados_revenda_do_cliente(cliente):
    tipo = str(cliente.get("tipo") or "").strip().upper()
    if tipo == "JURÍDICA":
        tipo = "JURIDICA"
    elif tipo == "FÍSICA":
        tipo = "FISICA"

    origem = {
        "nome": cliente.get("nome"),
        "tipo_pessoa": tipo if tipo in {"FISICA", "JURIDICA"} else None,
        "documento": cliente.get("documento"),
        "email": cliente.get("email"),
        "telefone": cliente.get("telefone_comercial"),
        "telefone_celular": cliente.get("telefone_celular"),
        "site": cliente.get("site"),
        "cep": cliente.get("cep"),
        "logradouro": cliente.get("logradouro"),
        "numero": cliente.get("numero"),
        "complemento": cliente.get("complemento"),
        "bairro": cliente.get("bairro"),
        "cidade": cliente.get("cidade"),
        "estado": cliente.get("estado"),
        "observacao": cliente.get("observacoes"),
        "limite_credito": cliente.get("limite_credito"),
        "permitir_exceder_limite": cliente.get("permitir_exceder"),
    }
    return {
        campo: valor
        for campo, valor in origem.items()
        if valor is not None and (not isinstance(valor, str) or valor.strip())
    }


def reclassificar_como_revenda(
    db: Session,
    cliente_id: int,
    data: ClienteReclassificarRevenda,
    tenant: TenantContext,
):
    empresa_id = require_tenant(tenant)
    if tenant.user_id is None or not str(tenant.user_id).strip():
        raise PermissionError("É necessário um usuário autenticado para reclassificar o cliente.")

    bind = getattr(db, "bind", None)
    dialect = getattr(getattr(bind, "dialect", None), "name", None)
    lock_clause = " FOR UPDATE" if dialect == "postgresql" else ""

    try:
        cliente_row = db.execute(
            text(
                "SELECT * FROM clientes "
                "WHERE id = :cliente_id AND empresa_id = :empresa_id"
                + lock_clause
            ),
            {"cliente_id": cliente_id, "empresa_id": empresa_id},
        ).mappings().first()
        if cliente_row is None:
            db.rollback()
            return None
        cliente = dict(cliente_row)

        link_existente = db.execute(
            text(
                """
                SELECT *
                FROM parceiros_comerciais
                WHERE empresa_id = :empresa_id
                  AND cliente_origem_id = :cliente_id
                """
                + lock_clause
            ),
            {"empresa_id": empresa_id, "cliente_id": cliente_id},
        ).mappings().first()
        if link_existente is not None:
            db.commit()
            return _parceiro_response(dict(link_existente))

        dados = _normalizar_textos(data.model_dump())
        dados.update(_dados_revenda_do_cliente(cliente))
        dados = _normalizar_textos(dados)
        dados["documento"] = _normalizar_documento(dados.get("documento"))
        if dados.get("cep"):
            cep = re.sub(r"\D", "", dados["cep"])
            if len(cep) != 8:
                raise ValueError("CEP do cadastro deve conter oito dígitos.")
            dados["cep"] = cep
        dados["percentual_padrao"] = _percentual_parceiro(dados["percentual_padrao"])
        dados["limite_credito"] = _limite_credito(dados.get("limite_credito"))
        dados["percentual_padrao"] = str(dados["percentual_padrao"])
        if dados["limite_credito"] is not None:
            dados["limite_credito"] = str(dados["limite_credito"])
        _validar_consistencia_fiscal(dados)
        _validar_vendedor_empresa(
            db, empresa_id, dados.get("vendedor_responsavel_id")
        )

        cnpj = _valor_cnpj(dados.get("documento"))
        if cnpj and dialect == "postgresql":
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:chave, 0))"),
                {"chave": f"revenda:{empresa_id}:{cnpj}"},
            )

        candidatos = []
        if cnpj:
            registros = db.execute(
                text(
                    "SELECT * FROM parceiros_comerciais "
                    "WHERE empresa_id = :empresa_id"
                    + lock_clause
                ),
                {"empresa_id": empresa_id},
            ).mappings().all()
            candidatos = [
                dict(registro)
                for registro in registros
                if _valor_cnpj(registro.get("documento")) == cnpj
            ]
        if len(candidatos) > 1:
            raise ValueError(
                "Há mais de uma revenda com este CNPJ nesta empresa. "
                "Resolva a duplicidade antes de reclassificar."
            )

        origem = dict(dados)
        if candidatos:
            parceiro = candidatos[0]
            cliente_vinculado = parceiro.get("cliente_origem_id")
            if cliente_vinculado is not None and int(cliente_vinculado) != cliente_id:
                raise ValueError(
                    "A revenda com este CNPJ já está vinculada a outro cliente."
                )

            atualizacoes = {
                campo: origem[campo]
                for campo in _PARCEIRO_FIELDS
                if origem.get(campo) is not None
                and parceiro.get(campo) in (None, "")
            }
            if atualizacoes:
                assignments = ", ".join(
                    f"{campo} = :{campo}" for campo in atualizacoes
                )
                db.execute(
                    text(
                        f"""
                        UPDATE parceiros_comerciais
                        SET {assignments},
                            cliente_origem_id = :cliente_id,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = :parceiro_id
                          AND empresa_id = :empresa_id
                        """
                    ),
                    {
                        **atualizacoes,
                        "cliente_id": cliente_id,
                        "parceiro_id": parceiro["id"],
                        "empresa_id": empresa_id,
                    },
                )
            else:
                db.execute(
                    text(
                        """
                        UPDATE parceiros_comerciais
                        SET cliente_origem_id = :cliente_id,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = :parceiro_id
                          AND empresa_id = :empresa_id
                        """
                    ),
                    {
                        "cliente_id": cliente_id,
                        "parceiro_id": parceiro["id"],
                        "empresa_id": empresa_id,
                    },
                )
            parceiro_id = parceiro["id"]
        else:
            fields = ", ".join(_PARCEIRO_FIELDS)
            values = ", ".join(f":{campo}" for campo in _PARCEIRO_FIELDS)
            parceiro = db.execute(
                text(
                    f"""
                    INSERT INTO parceiros_comerciais (
                        empresa_id, cliente_origem_id, {fields}
                    )
                    VALUES (
                        :empresa_id, :cliente_id, {values}
                    )
                    RETURNING *
                    """
                ),
                {
                    "empresa_id": empresa_id,
                    "cliente_id": cliente_id,
                    **{campo: dados.get(campo) for campo in _PARCEIRO_FIELDS},
                },
            ).mappings().one()
            parceiro_id = parceiro["id"]

        db.execute(
            text(
                """
                INSERT INTO cliente_reclassificacoes (
                    empresa_id, cliente_id, parceiro_id,
                    categoria_anterior, categoria_nova, usuario_id
                )
                VALUES (
                    :empresa_id, :cliente_id, :parceiro_id,
                    'CLIENTE', 'REVENDA', :usuario_id
                )
                """
            ),
            {
                "empresa_id": empresa_id,
                "cliente_id": cliente_id,
                "parceiro_id": parceiro_id,
                "usuario_id": str(tenant.user_id),
            },
        )

        result = db.execute(
            text(
                "SELECT * FROM parceiros_comerciais "
                "WHERE id = :parceiro_id AND empresa_id = :empresa_id"
            ),
            {"parceiro_id": parceiro_id, "empresa_id": empresa_id},
        ).mappings().one()
        db.commit()
        return _parceiro_response(dict(result))
    except Exception:
        db.rollback()
        raise
