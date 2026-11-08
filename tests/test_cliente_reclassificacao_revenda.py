import unittest
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.schemas.cliente import ClienteReclassificarRevenda
from app.services import cliente_service, representante_service
from app.tenant.context import TenantContext


class ClienteReclassificacaoRevendaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        with self.engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys = ON")
            connection.connection.driver_connection.executescript(
                """
                CREATE TABLE empresas (id INTEGER PRIMARY KEY);
                CREATE TABLE clientes (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    situacao TEXT,
                    nome TEXT NOT NULL,
                    email TEXT,
                    telefone_comercial TEXT,
                    telefone_celular TEXT,
                    documento TEXT,
                    site TEXT,
                    vendedor_responsavel TEXT,
                    parceiro_id INTEGER,
                    representante_id INTEGER,
                    cep TEXT,
                    logradouro TEXT,
                    numero TEXT,
                    complemento TEXT,
                    bairro TEXT,
                    cidade TEXT,
                    estado TEXT,
                    limite_credito NUMERIC DEFAULT 0,
                    permitir_exceder BOOLEAN DEFAULT FALSE,
                    observacoes TEXT,
                    UNIQUE (id, empresa_id),
                    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
                );
                CREATE TABLE parceiros_comerciais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER NOT NULL,
                    nome VARCHAR(255) NOT NULL,
                    documento VARCHAR(30),
                    email VARCHAR(255),
                    telefone VARCHAR(50),
                    percentual_padrao NUMERIC NOT NULL DEFAULT 0,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    observacao TEXT,
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP,
                    tipo_pessoa VARCHAR(8),
                    nome_fantasia VARCHAR(255),
                    razao_social VARCHAR(255),
                    situacao_cadastral VARCHAR(100),
                    inscricao_estadual VARCHAR(80),
                    inscricao_municipal VARCHAR(80),
                    tipo_contribuinte VARCHAR(30),
                    isento_ie BOOLEAN NOT NULL DEFAULT FALSE,
                    telefone_celular VARCHAR(50),
                    responsavel VARCHAR(120),
                    site VARCHAR(500),
                    cep VARCHAR(8),
                    logradouro VARCHAR(255),
                    numero VARCHAR(30),
                    complemento VARCHAR(255),
                    bairro VARCHAR(100),
                    cidade VARCHAR(150),
                    estado VARCHAR(2),
                    vendedor_responsavel_id INTEGER,
                    limite_credito NUMERIC,
                    permitir_exceder_limite BOOLEAN NOT NULL DEFAULT FALSE,
                    cliente_origem_id INTEGER,
                    UNIQUE (id, empresa_id),
                    UNIQUE (empresa_id, cliente_origem_id),
                    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                    FOREIGN KEY (cliente_origem_id, empresa_id)
                        REFERENCES clientes(id, empresa_id)
                );
                CREATE TABLE cliente_reclassificacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER NOT NULL,
                    cliente_id INTEGER NOT NULL,
                    parceiro_id INTEGER NOT NULL,
                    categoria_anterior TEXT NOT NULL,
                    categoria_nova TEXT NOT NULL,
                    usuario_id TEXT NOT NULL,
                    registrado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cliente_id, empresa_id)
                        REFERENCES clientes(id, empresa_id),
                    FOREIGN KEY (parceiro_id, empresa_id)
                        REFERENCES parceiros_comerciais(id, empresa_id)
                );
                CREATE TABLE orcamentos (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER NOT NULL,
                    cliente_id INTEGER,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                );
                CREATE TABLE pedidos (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER NOT NULL,
                    cliente_id INTEGER,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                );
                """
            )
            connection.exec_driver_sql("INSERT INTO empresas (id) VALUES (1), (2)")
            connection.exec_driver_sql(
                """
                INSERT INTO clientes (
                    id, empresa_id, tipo, situacao, nome, documento, email,
                    telefone_comercial, telefone_celular, cep, logradouro, numero,
                    complemento, bairro, cidade, estado, limite_credito,
                    permitir_exceder, observacoes
                ) VALUES (
                    101, 1, 'Jurídica', 'Ativo', 'NDECOR',
                    '11.222.333/0001-81', 'financeiro@ndecor.example',
                    '(11) 3333-4444', '(11) 99999-8888', '01001-000',
                    'Praça da Sé', '10', 'Sala 2', 'Sé', 'São Paulo', 'SP',
                    2500, TRUE, 'Cadastro histórico do cliente'
                ), (
                    202, 2, 'Jurídica', 'Ativo', 'Outra empresa',
                    '11.222.333/0001-81', NULL, NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL, NULL, NULL, 0, FALSE, NULL
                )
                """
            )
            connection.exec_driver_sql(
                "INSERT INTO orcamentos (id, empresa_id, cliente_id) VALUES (301, 1, 101)"
            )
            connection.exec_driver_sql(
                "INSERT INTO pedidos (id, empresa_id, cliente_id) VALUES (401, 1, 101)"
            )
        self.db = Session(self.engine)
        self.tenant = TenantContext(empresa_id=1, user_id=77)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _payload(self, **changes):
        values = {
            "nome": "Nome preenchido no formulário",
            "documento": "11.222.333/0001-81",
            "percentual_padrao": Decimal("0"),
        }
        values.update(changes)
        return ClienteReclassificarRevenda(**values)

    def _parceiro(self, empresa_id, **changes):
        values = {
            "nome": "Revenda existente",
            "documento": "11222333000181",
            "percentual_padrao": 12,
            "ativo": True,
            "isento_ie": False,
            "permitir_exceder_limite": False,
        }
        values.update(changes)
        columns = ", ".join(("empresa_id", *values))
        markers = ", ".join(f":{column}" for column in ("empresa_id", *values))
        result = self.db.execute(
            text(
                f"INSERT INTO parceiros_comerciais ({columns}) "
                f"VALUES ({markers}) RETURNING id"
            ),
            {"empresa_id": empresa_id, **values},
        ).scalar_one()
        self.db.commit()
        return result

    def _reclassificar(self, cliente_id=101, tenant=None, payload=None):
        return cliente_service.reclassificar_como_revenda(
            self.db,
            cliente_id,
            payload or self._payload(),
            tenant or self.tenant,
        )

    def test_preserva_cliente_e_referencias_a_orcamento_e_pedido(self):
        antes = cliente_service.get_all(self.db, self.tenant)
        self.assertEqual([cliente.id for cliente in antes], [101])

        revenda = self._reclassificar()

        self.db.expire_all()
        self.assertEqual(revenda["nome"], "NDECOR")
        self.assertEqual(revenda["documento"], "11222333000181")
        self.assertEqual(revenda["tipo_pessoa"], "JURIDICA")
        self.assertEqual(revenda["email"], "financeiro@ndecor.example")
        self.assertEqual(revenda["telefone"], "(11) 3333-4444")
        self.assertEqual(revenda["telefone_celular"], "(11) 99999-8888")
        self.assertEqual(revenda["cep"], "01001000")
        self.assertEqual(revenda["logradouro"], "Praça da Sé")
        self.assertEqual(revenda["numero"], "10")
        self.assertEqual(revenda["observacao"], "Cadastro histórico do cliente")
        self.assertEqual(
            self.db.execute(text("SELECT cliente_id FROM orcamentos WHERE id = 301")).scalar_one(),
            101,
        )
        self.assertEqual(
            self.db.execute(text("SELECT cliente_id FROM pedidos WHERE id = 401")).scalar_one(),
            101,
        )
        self.assertEqual(self.db.execute(text("SELECT nome FROM clientes WHERE id = 101")).scalar_one(), "NDECOR")
        self.assertEqual(cliente_service.get_all(self.db, self.tenant), [])
        revendas = representante_service.listar_parceiros(self.db, self.tenant)
        self.assertEqual([row["id"] for row in revendas], [revenda["id"]])
        self.assertEqual(
            self.db.execute(
                text("SELECT usuario_id FROM cliente_reclassificacoes")
            ).scalar_one(),
            "77",
        )

    def test_reutiliza_revenda_com_mesmo_cnpj_sem_duplicar(self):
        existing_id = self._parceiro(
            1, nome="NDECOR cadastrado", email="contato@ndecor.example"
        )

        first = self._reclassificar()
        second = self._reclassificar()

        self.assertEqual(first["id"], existing_id)
        self.assertEqual(second["id"], existing_id)
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM parceiros_comerciais")).scalar_one(),
            1,
        )
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM cliente_reclassificacoes")).scalar_one(),
            1,
        )
        self.assertEqual(first["email"], "contato@ndecor.example")
        self.assertEqual(first["telefone"], "(11) 3333-4444")

    def test_cnpj_igual_em_outra_empresa_nao_reutiliza_cadastro(self):
        self._parceiro(2, nome="Revenda de outra empresa")

        result = self._reclassificar()

        self.assertNotEqual(result["id"], 1)
        self.assertEqual(result["empresa_id"], 1)
        self.assertEqual(
            self.db.execute(
                text("SELECT count(*) FROM parceiros_comerciais WHERE empresa_id = 1")
            ).scalar_one(),
            1,
        )
        clientes_empresa_dois = cliente_service.get_all(
            self.db, TenantContext(empresa_id=2, user_id=88)
        )
        self.assertEqual([cliente.id for cliente in clientes_empresa_dois], [202])

    def test_reutiliza_cnpj_alfanumerico(self):
        self.db.execute(
            text("""
                INSERT INTO clientes (id, empresa_id, tipo, nome, documento)
                VALUES (303, 1, 'Jurídica', 'Empresa alfanumérica', '12.ABC.345/01DE-35')
            """)
        )
        self.db.commit()
        existing_id = self._parceiro(
            1, nome="Empresa alfanumérica", documento="12ABC34501DE35"
        )

        result = self._reclassificar(
            cliente_id=303,
            payload=self._payload(documento="12.ABC.345/01DE-35"),
        )

        self.assertEqual(result["id"], existing_id)
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM parceiros_comerciais")).scalar_one(),
            1,
        )

    def test_cliente_de_outra_empresa_nao_e_encontrado(self):
        result = self._reclassificar(
            cliente_id=101,
            tenant=TenantContext(empresa_id=2, user_id=88),
        )

        self.assertIsNone(result)
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM parceiros_comerciais")).scalar_one(),
            0,
        )
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM cliente_reclassificacoes")).scalar_one(),
            0,
        )

    def test_rolls_back_revenda_se_a_auditoria_falhar(self):
        self.db.execute(
            text("""
                CREATE TRIGGER falha_auditoria
                BEFORE INSERT ON cliente_reclassificacoes
                BEGIN
                    SELECT RAISE(ABORT, 'falha simulada de auditoria');
                END
            """)
        )
        self.db.commit()

        with self.assertRaisesRegex(Exception, "falha simulada de auditoria"):
            self._reclassificar()

        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM parceiros_comerciais")).scalar_one(),
            0,
        )
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM cliente_reclassificacoes")).scalar_one(),
            0,
        )
        self.assertIsNone(
            self.db.execute(
                text("SELECT cliente_origem_id FROM parceiros_comerciais")
            ).first()
        )

    def test_exige_usuario_para_registrar_autoria(self):
        with self.assertRaisesRegex(PermissionError, "usuário autenticado"):
            self._reclassificar(tenant=TenantContext(empresa_id=1))
        self.assertEqual(
            self.db.execute(text("SELECT count(*) FROM parceiros_comerciais")).scalar_one(),
            0,
        )


if __name__ == "__main__":
    unittest.main()
