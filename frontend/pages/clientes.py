from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import conectar

router = APIRouter(prefix="/clientes", tags=["Clientes"])


class Cliente(BaseModel):
    nome: str
    documento: str = ""
    telefone: str = ""
    tipo_cliente: str = "Cliente final"
    lojista_id: int | None = None
    representante_id: int | None = None


@router.get("/")
def listar_clientes():
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            nome,
            documento,
            telefone,
            tipo_cliente,
            lojista_id,
            representante_id
        FROM clientes
        ORDER BY id DESC
        """
    )

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "id": item[0],
            "nome": item[1],
            "documento": item[2],
            "telefone": item[3],
            "tipo_cliente": item[4],
            "lojista_id": item[5],
            "representante_id": item[6],
        }
        for item in dados
    ]


@router.post("/")
def criar_cliente(cliente: Cliente):

    # ======================
    # REGRAS DE NEGÓCIO
    # ======================

    # 🔴 LOJISTA sempre precisa de documento
    if cliente.tipo_cliente == "Lojista" and not cliente.documento:
        raise HTTPException(
            status_code=400,
            detail="Documento obrigatório para lojista"
        )

    # 🟡 REPRESENTANTE
    if cliente.tipo_cliente == "Representante":
        # Se NÃO tem lojista → é seu → documento obrigatório
        if not cliente.lojista_id and not cliente.documento:
            raise HTTPException(
                status_code=400,
                detail="Documento obrigatório para representante direto"
            )
        # Se tem lojista → documento opcional (regra que você pediu)

    # 🟢 CLIENTE FINAL → sempre opcional (não faz nada)

    # ======================
    # INSERT
    # ======================
    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO clientes (
            nome,
            documento,
            telefone,
            tipo_cliente,
            lojista_id,
            representante_id
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            cliente.nome,
            cliente.documento or None,
            cliente.telefone,
            cliente.tipo_cliente,
            cliente.lojista_id,
            cliente.representante_id,
        ),
    )

    novo_id = cur.fetchone()[0]
    conn.commit()

    cur.close()
    conn.close()

    return {
        "id": novo_id,
        "nome": cliente.nome,
        "documento": cliente.documento,
        "telefone": cliente.telefone,
        "tipo_cliente": cliente.tipo_cliente,
        "lojista_id": cliente.lojista_id,
        "representante_id": cliente.representante_id,
    }


@router.put("/{cliente_id}")
def atualizar_cliente(cliente_id: int, cliente: Cliente):

    conn = conectar()
    cur = conn.cursor()

    # ======================
    # REGRAS DE NEGÓCIO
    # ======================

    if cliente.tipo_cliente == "Lojista" and not cliente.documento:
        raise HTTPException(
            status_code=400,
            detail="Documento obrigatório para lojista"
        )

    if cliente.tipo_cliente == "Representante":
        if not cliente.lojista_id and not cliente.documento:
            raise HTTPException(
                status_code=400,
                detail="Documento obrigatório para representante direto"
            )

    # ======================
    # UPDATE
    # ======================

    cur.execute(
        """
        UPDATE clientes
        SET
            nome = %s,
            documento = %s,
            telefone = %s,
            tipo_cliente = %s,
            lojista_id = %s,
            representante_id = %s
        WHERE id = %s
        """,
        (
            cliente.nome,
            cliente.documento or None,
            cliente.telefone,
            cliente.tipo_cliente,
            cliente.lojista_id,
            cliente.representante_id,
            cliente_id,
        ),
    )

    conn.commit()

    cur.close()
    conn.close()

    return {"ok": True}
