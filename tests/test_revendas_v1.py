import os
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.routes import consultas_cadastro as consultas_routes
from app.routes import representante as representante_routes
from app.schemas.consultas_cadastro import ConsultaCEPInput, ConsultaCNPJInput
from app.schemas.representante import ParceiroCreate, ParceiroUpdate
from app.services import consultas_cadastro_adapters as cadastro_adapters
from app.services import consultas_cadastro_service as consultas
from app.services import representante_service as parceiros
from app.services.consultas_cadastro_adapters import ConsultaCadastroError
from app.tenant.context import TenantContext


ROOT = Path(__file__).resolve().parents[1]
TENANT = TenantContext(empresa_id=17)


def _parceiro(**changes):
    row = {
        "id": 8,
        "empresa_id": 17,
        "nome": "Loja Exemplo",
        "documento": "11222333000181",
        "email": None,
        "telefone": None,
        "percentual_padrao": Decimal("0.0000"),
        "ativo": True,
        "observacao": None,
        "criado_em": None,
        "atualizado_em": None,
        "tipo_pessoa": None,
        "nome_fantasia": None,
        "razao_social": None,
        "situacao_cadastral": None,
        "inscricao_estadual": None,
        "inscricao_municipal": None,
        "tipo_contribuinte": None,
        "isento_ie": False,
        "telefone_celular": None,
        "responsavel": None,
        "site": None,
        "cep": None,
        "logradouro": None,
        "numero": None,
        "complemento": None,
        "bairro": None,
        "cidade": None,
        "estado": None,
        "vendedor_responsavel_id": None,
        "limite_credito": None,
        "permitir_exceder_limite": False,
    }
    row.update(changes)
    return row


class ParceiroServiceTests(unittest.TestCase):
    def test_create_legado_normaliza_documento_e_mantem_limite_indefinido(self):
        returned = _parceiro(documento="11222333000181")
        db = Mock()
        db.execute.return_value.mappings.return_value.one.return_value = returned

        result = parceiros.criar_parceiro(
            db, TENANT, ParceiroCreate(nome="  Loja Exemplo ", documento="11.222.333/0001-81")
        )

        sql, params = db.execute.call_args.args
        self.assertIn("INSERT INTO parceiros_comerciais", str(sql))
        self.assertEqual(params["empresa_id"], 17)
        self.assertEqual(params["nome"], "Loja Exemplo")
        self.assertEqual(params["documento"], "11222333000181")
        self.assertIsNone(params["limite_credito"])
        self.assertEqual(result["id"], 8)
        existing_fields = {
            "id", "empresa_id", "nome", "documento", "email", "telefone",
            "percentual_padrao", "ativo", "observacao", "criado_em", "atualizado_em",
        }
        canonical_v1_fields = {
            "tipo_pessoa", "nome_fantasia", "razao_social", "situacao_cadastral",
            "inscricao_estadual", "inscricao_municipal", "tipo_contribuinte",
            "isento_ie", "telefone_celular", "responsavel", "site", "cep",
            "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
            "vendedor_responsavel_id", "limite_credito", "permitir_exceder_limite",
        }
        self.assertEqual(len(canonical_v1_fields), 21)
        self.assertEqual(set(result), existing_fields | canonical_v1_fields)
        db.commit.assert_called_once()

    def test_create_normaliza_documento_alfanumerico_sem_exigir_checksum(self):
        returned = _parceiro(documento="12ABC34501DE35")
        db = Mock()
        db.execute.return_value.mappings.return_value.one.return_value = returned
        parceiros.criar_parceiro(
            db,
            TENANT,
            ParceiroCreate(nome="Loja", documento="12.abc.345/01de-35"),
        )
        self.assertEqual(db.execute.call_args.args[1]["documento"], "12ABC34501DE35")

    def test_create_financeiro_quantiza_zero_e_percentual(self):
        db = Mock()
        db.execute.return_value.mappings.return_value.one.return_value = _parceiro(
            limite_credito=Decimal("0.00"),
            percentual_padrao=Decimal("12.3457"),
        )
        parceiros.criar_parceiro(
            db,
            TENANT,
            ParceiroCreate(
                nome="Loja",
                percentual_padrao=Decimal("12.34567"),
                limite_credito=Decimal("0"),
            ),
        )
        params = db.execute.call_args.args[1]
        self.assertEqual(params["percentual_padrao"], Decimal("12.3457"))
        self.assertEqual(params["limite_credito"], Decimal("0.00"))

    def test_patch_preserva_null_explicitamente_e_isola_empresa(self):
        db = Mock()
        existing = _parceiro(email="contato@example.test", limite_credito=Decimal("50.00"))
        db.execute.side_effect = [
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=existing)))),
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=_parceiro(
                email=None, limite_credito=None
            ))))),
        ]

        result = parceiros.atualizar_parceiro(
            db,
            TENANT,
            8,
            ParceiroUpdate(email=None, limite_credito=None),
        )

        update_sql, update_params = db.execute.call_args.args
        self.assertIn("empresa_id = :empresa_id", str(update_sql))
        self.assertEqual(update_params["empresa_id"], 17)
        self.assertIsNone(update_params["email"])
        self.assertIsNone(update_params["limite_credito"])
        self.assertIsNone(result["limite_credito"])
        db.commit.assert_called_once()

    def test_patch_fiscal_validates_merged_state_not_partial_payload(self):
        existing = _parceiro(isento_ie=True, tipo_contribuinte="ISENTO")
        for update in (
            ParceiroUpdate(tipo_contribuinte="ISENTO"),
            ParceiroUpdate(isento_ie=True),
        ):
            updated = dict(existing)
            db = Mock()
            db.execute.side_effect = [
                Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=existing)))),
                Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=updated)))),
            ]
            result = parceiros.atualizar_parceiro(db, TENANT, 8, update)
            self.assertTrue(result["isento_ie"])
            self.assertEqual(result["tipo_contribuinte"], "ISENTO")
            db.commit.assert_called_once()

    def test_patch_rejects_contradictory_merged_fiscal_state(self):
        existing = _parceiro(isento_ie=True, tipo_contribuinte="ISENTO")
        db = Mock()
        db.execute.return_value.mappings.return_value.first.return_value = existing
        with self.assertRaisesRegex(ValueError, "exige"):
            parceiros.atualizar_parceiro(
                db, TENANT, 8, ParceiroUpdate(tipo_contribuinte="CONTRIBUINTE")
            )
        db.commit.assert_not_called()

    def test_patch_nome_nao_encontrado_na_empresa_nao_atualiza(self):
        db = Mock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        self.assertIsNone(
            parceiros.atualizar_parceiro(
                db, TENANT, 999, ParceiroUpdate(nome="Não autorizado")
            )
        )
        db.commit.assert_not_called()
        self.assertEqual(db.execute.call_count, 1)

    def test_busca_parceiro_usa_tenant_e_allowlist_de_resposta(self):
        returned = _parceiro(campo_privado="não retornar")
        db = Mock()
        db.execute.return_value.mappings.return_value.first.return_value = returned
        result = parceiros.buscar_parceiro(db, TENANT, 8)
        sql, params = db.execute.call_args.args
        self.assertIn("id = :parceiro_id", str(sql))
        self.assertIn("empresa_id = :empresa_id", str(sql))
        self.assertEqual(params, {"parceiro_id": 8, "empresa_id": 17})
        self.assertNotIn("campo_privado", result)

    def test_vendedor_de_outra_empresa_e_rejeitado(self):
        db = Mock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        with self.assertRaisesRegex(ValueError, "empresa atual"):
            parceiros.criar_parceiro(
                db,
                TENANT,
                ParceiroCreate(nome="Loja", vendedor_responsavel_id=4),
            )
        query, parameters = db.execute.call_args.args
        self.assertIn("empresa_id = :empresa_id", str(query))
        self.assertEqual(parameters, {"vendedor_id": 4, "empresa_id": TENANT.empresa_id})
        db.commit.assert_not_called()

    def test_patch_rejeita_vendedor_de_outra_empresa(self):
        db = Mock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        with self.assertRaisesRegex(ValueError, "empresa atual"):
            parceiros.atualizar_parceiro(
                db, TENANT, 8, ParceiroUpdate(vendedor_responsavel_id=4)
            )
        query, parameters = db.execute.call_args.args
        self.assertIn("empresa_id = :empresa_id", str(query))
        self.assertEqual(parameters, {"vendedor_id": 4, "empresa_id": TENANT.empresa_id})
        db.commit.assert_not_called()

    def test_api_ignora_empresa_enviada_pelo_navegador(self):
        returned = _parceiro()
        db = Mock()
        db.execute.return_value.mappings.return_value.one.return_value = returned

        data = ParceiroCreate(nome="Loja")
        object.__setattr__(data, "empresa_id", 999)
        representante_routes.criar_parceiro(data, db, TENANT)

        _, parameters = db.execute.call_args.args
        self.assertEqual(parameters["empresa_id"], TENANT.empresa_id)
        db.commit.assert_called_once()

    def test_api_rejeita_vendedor_de_outra_empresa(self):
        db = Mock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as error:
            representante_routes.criar_parceiro(
                ParceiroCreate(nome="Loja", vendedor_responsavel_id=4),
                db,
                TENANT,
            )
        self.assertEqual(error.exception.status_code, 400)
        db.commit.assert_not_called()

    def test_vendedor_inativo_da_mesma_empresa_pode_ser_preservado_no_patch(self):
        existing = _parceiro(vendedor_responsavel_id=5)
        updated = _parceiro(vendedor_responsavel_id=5)
        db = Mock()
        db.execute.side_effect = [
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value={
                "id": 5, "situacao": "Inativo"
            })))),
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=existing)))),
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=updated)))),
        ]

        result = parceiros.atualizar_parceiro(
            db,
            TENANT,
            8,
            ParceiroUpdate(vendedor_responsavel_id=5),
        )

        vendor_sql = str(db.execute.call_args_list[0].args[0])
        self.assertIn("empresa_id = :empresa_id", vendor_sql)
        self.assertNotIn("ativo", vendor_sql.lower())
        self.assertEqual(result["vendedor_responsavel_id"], 5)
        db.commit.assert_called_once()

    def test_valores_financeiros_invalidos_sao_rejeitados(self):
        for value in (
            Decimal("-0.01"), Decimal("-0.001"), Decimal("Infinity"), Decimal("NaN"),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parceiros._limite_credito(value)
        with self.assertRaisesRegex(ValueError, "entre 0 e 100"):
            parceiros._percentual_parceiro(Decimal("100.01"))
        with self.assertRaisesRegex(ValueError, "entre 0 e 100"):
            parceiros._percentual_parceiro(Decimal("100.00001"))
        self.assertEqual(
            parceiros._percentual_parceiro(Decimal("99.99999")),
            Decimal("100.0000"),
        )


class ParceiroSchemaTests(unittest.TestCase):
    def test_patch_rejeita_campo_desconhecido_e_null_nao_nulo(self):
        with self.assertRaises(ValidationError):
            ParceiroUpdate(nome="Loja", campo_inseguro="valor")
        with self.assertRaises(ValidationError):
            ParceiroCreate(nome="Loja", fornecedor_id=7)
        with self.assertRaises(ValidationError):
            ParceiroUpdate(fornecedor="Fornecedor")
        with self.assertRaises(ValidationError):
            ParceiroUpdate(ativo=None)
        with self.assertRaises(ValidationError):
            ParceiroUpdate(percentual_padrao=None)
        with self.assertRaises(ValidationError):
            ParceiroCreate(nome="Loja", vendedor_responsavel_id=0)

    def test_uf_e_consistencia_fiscal(self):
        self.assertEqual(ParceiroCreate(nome="Loja", estado=" sp ").estado, "SP")
        with self.assertRaises(ValidationError):
            ParceiroCreate(nome="Loja", estado="XX")
        with self.assertRaises(ValidationError):
            ParceiroCreate(
                nome="Loja",
                inscricao_estadual="123",
                isento_ie=True,
                tipo_contribuinte="ISENTO",
            )
        with self.assertRaises(ValidationError):
            ParceiroCreate(nome="Loja", tipo_contribuinte="ISENTO")


class ConsultationServiceTests(unittest.TestCase):
    def test_service_uses_injected_adapter_without_provider_http_logic(self):
        response = consultas.ConsultaCadastroResponse(
            dados={"razao_social": "Via adapter"}, fonte="brasilapi"
        )
        fake_adapter = Mock()
        fake_adapter.consultar.return_value = response
        with patch.dict(
            cadastro_adapters._CNPJ_ADAPTERS, {"test-provider": fake_adapter}
        ), patch.dict(
            os.environ,
            {"SMARTTEC_CNPJ_CONSULTA_PROVIDER": "test-provider"},
        ):
            result = consultas.consultar_cnpj("11222333000181")
        fake_adapter.consultar.assert_called_once_with("11222333000181")
        self.assertIs(result, response)

    def test_cnpj_uses_provider_fixed_url_and_allowlisted_response(self):
        payload = {
            "cnpj": "11222333000181",
            "razao_social": "Empresa Exemplo Ltda",
            "nome_fantasia": "Exemplo",
            "descricao_situacao_cadastral": "ATIVA",
            "email": "CONTATO@EXAMPLE.TEST",
            "ddd_telefone_1": "1133334444",
            "cep": "01310930",
            "logradouro": "Avenida Exemplo",
            "bairro": "Bela Vista",
            "municipio": "São Paulo",
            "uf": "SP",
            "inscricoes_estaduais": [
                {"inscricao_estadual": "123456789", "uf": "SP", "ativo": True},
            ],
            "dados_internos": "não expor",
        }
        response = Mock(status_code=200)
        response.json.return_value = payload
        with patch.object(cadastro_adapters.requests, "get", return_value=response) as get:
            result = consultas.consultar_cnpj("11.222.333/0001-81")

        get.assert_called_once_with(
            "https://brasilapi.com.br/api/cnpj/v1/11222333000181",
            timeout=(3.05, 10),
            allow_redirects=False,
        )
        self.assertEqual(result.fonte, "brasilapi")
        self.assertEqual(result.dados.email, "contato@example.test")
        self.assertEqual(result.dados.telefone_comercial, "1133334444")
        self.assertEqual(result.dados.inscricao_estadual, "123456789")
        serialized = result.dict(exclude_none=True)
        self.assertEqual(set(serialized), {"dados", "fonte", "consultado_em"})
        self.assertEqual(
            set(serialized["dados"]),
            {
                "razao_social", "nome_fantasia", "situacao_cadastral", "email",
                "telefone_comercial", "inscricao_estadual", "cep", "logradouro",
                "bairro", "cidade", "estado",
            },
        )
        self.assertNotIn("dados_internos", serialized["dados"])
        self.assertNotIn("numero", serialized["dados"])

    def test_cnpj_aproveita_segundo_telefone_tipo_logradouro_e_situacao_numerica(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "cnpj": "11222333000181",
            "razao_social": " Empresa Exemplo ",
            "nome_fantasia": " Loja Exemplo ",
            "email": " CONTATO@EXAMPLE.TEST ",
            "ddd_telefone_1": "",
            "ddd_telefone_2": "11987654321",
            "situacao_cadastral": 2,
            "descricao_tipo_de_logradouro": "AVENIDA",
            "logradouro": "Paulista",
            "numero": "100",
            "complemento": "Sala 2",
            "bairro": "Bela Vista",
            "municipio": "São Paulo",
            "cep": "01310-930",
            "uf": "sp",
        }
        with patch.object(cadastro_adapters.requests, "get", return_value=response):
            dados = consultas.consultar_cnpj("11222333000181").dados
        self.assertEqual(dados.razao_social, "Empresa Exemplo")
        self.assertEqual(dados.nome_fantasia, "Loja Exemplo")
        self.assertEqual(dados.email, "contato@example.test")
        self.assertEqual(dados.telefone_comercial, "11987654321")
        self.assertEqual(dados.situacao_cadastral, "ATIVA")
        self.assertEqual(dados.logradouro, "AVENIDA Paulista")
        self.assertEqual(dados.numero, "100")
        self.assertEqual(dados.complemento, "Sala 2")
        self.assertEqual(dados.bairro, "Bela Vista")
        self.assertEqual(dados.cidade, "São Paulo")
        self.assertEqual(dados.cep, "01310930")
        self.assertEqual(dados.estado, "SP")

    def test_cnpj_preserva_dois_telefones_sem_inferir_celular_e_sem_duplicar(self):
        for primeiro, segundo, esperado in (
            ("1133334444", "11987654321", "1133334444 / 11987654321"),
            ("(11) 3333-4444", "1133334444", "(11) 3333-4444"),
            ("1133334444", None, "1133334444"),
            (None, None, None),
        ):
            with self.subTest(primeiro=primeiro, segundo=segundo):
                response = Mock(status_code=200)
                response.json.return_value = {
                    "cnpj": "11222333000181",
                    "ddd_telefone_1": primeiro,
                    "ddd_telefone_2": segundo,
                }
                with patch.object(cadastro_adapters.requests, "get", return_value=response):
                    dados = consultas.consultar_cnpj("11222333000181").dados
                self.assertEqual(dados.telefone_comercial, esperado)

    def test_cnpj_nao_inventa_dados_ausentes_nem_duplica_tipo_logradouro(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "cnpj": "11222333000181",
            "nome_fantasia": " ",
            "email": None,
            "descricao_tipo_de_logradouro": "AVENIDA",
            "logradouro": "avenida Paulista",
            "descricao_situacao_cadastral": "ATIVA",
            "situacao_cadastral": 8,
        }
        with patch.object(cadastro_adapters.requests, "get", return_value=response):
            dados = consultas.consultar_cnpj("11222333000181").dados
        self.assertIsNone(dados.nome_fantasia)
        self.assertIsNone(dados.email)
        self.assertIsNone(dados.numero)
        self.assertIsNone(dados.complemento)
        self.assertEqual(dados.logradouro, "avenida Paulista")
        self.assertEqual(dados.situacao_cadastral, "ATIVA")

    def test_cnpj_mismatch_and_malformed_provider_data_are_sanitized(self):
        mismatch = Mock(status_code=200)
        mismatch.json.return_value = {"cnpj": "00000000000000"}
        with patch.object(cadastro_adapters.requests, "get", return_value=mismatch):
            with self.assertRaises(ConsultaCadastroError) as error:
                consultas.consultar_cnpj("11222333000181")
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("00000000000000", error.exception.detail)

        malformed = Mock(status_code=200)
        malformed.json.return_value = ["unexpected"]
        with patch.object(cadastro_adapters.requests, "get", return_value=malformed):
            with self.assertRaises(ConsultaCadastroError) as error:
                consultas.consultar_cnpj("11222333000181")
        self.assertEqual(error.exception.status_code, 502)

    def test_ie_requires_single_active_registration_for_returned_uf(self):
        cases = (
            (
                [{"inscricao_estadual": "111", "uf": "SP", "ativo": False}],
                None,
            ),
            (
                [{"inscricao_estadual": "111", "uf": "RJ", "ativo": True}],
                None,
            ),
            (
                [
                    {"inscricao_estadual": "111", "uf": "SP", "ativo": True},
                    {"inscricao_estadual": "222", "uf": "SP", "ativo": True},
                ],
                None,
            ),
            (
                [{"inscricao_estadual": "111", "uf": "SP", "ativo": True}],
                "111",
            ),
        )
        for records, expected in cases:
            with self.subTest(records=records):
                response = Mock(status_code=200)
                response.json.return_value = {
                    "cnpj": "11222333000181",
                    "uf": "SP",
                    "inscricoes_estaduais": records,
                }
                with patch.object(cadastro_adapters.requests, "get", return_value=response):
                    result = consultas.consultar_cnpj("11222333000181")
                self.assertEqual(result.dados.inscricao_estadual, expected)

    def test_malformed_provider_optional_fields_are_502(self):
        invalid_payloads = (
            {"cnpj": "11222333000181", "uf": "XX"},
            {"cnpj": "11222333000181", "ddd_telefone_1": 12345},
            {"cnpj": "11222333000181", "ddd_telefone_2": 12345},
            {"cnpj": "11222333000181", "situacao_cadastral": 999},
            {"cnpj": "11222333000181", "situacao_cadastral": True},
            {"cnpj": "11222333000181", "ddd_telefone_1": "1" * 30, "ddd_telefone_2": "2" * 30},
            {"cnpj": "11222333000181", "logradouro": "L" * 255, "descricao_tipo_de_logradouro": "AVENIDA"},
            {"cnpj": "11222333000181", "logradouro": "L" * 256},
            {"cnpj": "11222333000181", "cep": "123"},
            {
                "cnpj": "11222333000181",
                "inscricoes_estaduais": [
                    {"inscricao_estadual": "111", "uf": "SP", "ativo": "true"}
                ],
            },
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = Mock(status_code=200)
                response.json.return_value = payload
                with patch.object(cadastro_adapters.requests, "get", return_value=response):
                    with self.assertRaises(ConsultaCadastroError) as error:
                        consultas.consultar_cnpj("11222333000181")
                self.assertEqual(error.exception.status_code, 502)

    def test_cep_validates_matching_return_and_maps_not_found(self):
        payload = {
            "cep": "01310-930",
            "logradouro": "Avenida Paulista",
            "bairro": "Bela Vista",
            "localidade": "São Paulo",
            "uf": "SP",
            "unidade": "não expor",
        }
        response = Mock(status_code=200)
        response.json.return_value = payload
        with patch.object(cadastro_adapters.requests, "get", return_value=response) as get:
            result = consultas.consultar_cep("01310-930")
        get.assert_called_once_with(
            "https://viacep.com.br/ws/01310930/json/",
            timeout=(3.05, 10),
            allow_redirects=False,
        )
        self.assertEqual(
            set(result.dict(exclude_none=True)["dados"]),
            {"cep", "logradouro", "bairro", "cidade", "estado"},
        )
        self.assertEqual(result.dados.cidade, "São Paulo")

        missing = Mock(status_code=200)
        missing.json.return_value = {"erro": True}
        with patch.object(cadastro_adapters.requests, "get", return_value=missing):
            with self.assertRaises(ConsultaCadastroError) as error:
                consultas.consultar_cep("01310930")
        self.assertEqual(error.exception.status_code, 404)

    def test_timeout_and_provider_http_errors_are_mapped(self):
        with patch.object(
            cadastro_adapters.requests,
            "get",
            side_effect=cadastro_adapters.requests.exceptions.Timeout(),
        ):
            with self.assertRaises(ConsultaCadastroError) as error:
                consultas.consultar_cep("01310930")
        self.assertEqual(error.exception.status_code, 503)

        response = Mock(status_code=404)
        with patch.object(cadastro_adapters.requests, "get", return_value=response):
            with self.assertRaises(ConsultaCadastroError) as error:
                consultas.consultar_cep("01310930")
        self.assertEqual(error.exception.status_code, 404)

    def test_provider_can_be_disabled_and_unapproved_value_fails_closed(self):
        for value in ("off", "https://unapproved.invalid"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"SMARTTEC_CEP_CONSULTA_PROVIDER": value}
            ):
                with self.assertRaises(ConsultaCadastroError) as error:
                    consultas.consultar_cep("01310930")
                self.assertEqual(error.exception.status_code, 503)


class RevendasRouteTests(unittest.TestCase):
    def test_consultas_requerem_entrada_validada_e_resposta_do_provedor(self):
        with self.assertRaises(ValidationError):
            ConsultaCNPJInput(documento="00000000000000")

        payload = {
            "cnpj": "11222333000181",
            "razao_social": "Empresa Exemplo Ltda",
        }
        response = Mock(status_code=200)
        response.json.return_value = payload
        with patch.object(cadastro_adapters.requests, "get", return_value=response):
            result = consultas_routes.consultar_cnpj(
                ConsultaCNPJInput(documento="11222333000181"), TENANT
            )
        self.assertEqual(result.dados.razao_social, "Empresa Exemplo Ltda")

    def test_cadastro_rapido_legado_e_patch_null_preservado_na_api(self):
        created = _parceiro()
        create_db = Mock()
        create_db.execute.return_value.mappings.return_value.one.return_value = created
        created_response = representante_routes.criar_parceiro(
            ParceiroCreate(nome="Loja Exemplo"), create_db, TENANT
        )
        self.assertEqual(created_response["id"], 8)

        patch_db = Mock()
        patch_db.execute.side_effect = [
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=created)))),
            Mock(mappings=Mock(return_value=Mock(first=Mock(return_value=_parceiro(email=None))))),
        ]
        patch_response = representante_routes.atualizar_parceiro(
            8, ParceiroUpdate(email=None), patch_db, TENANT
        )
        self.assertIsNone(patch_response["email"])

    def test_routes_are_registered_at_expected_paths(self):
        routes = {
            (method, route.path)
            for router in (consultas_routes.router, representante_routes.router)
            for route in router.routes
            for method in getattr(route, "methods", ())
        }
        self.assertIn(("POST", "/cnpj"), routes)
        self.assertIn(("POST", "/cep"), routes)
        self.assertIn(("GET", "/parceiros/{parceiro_id}"), routes)
        self.assertIn(("PATCH", "/parceiros/{parceiro_id}"), routes)

    def test_consulta_error_becomes_sanitized_http_status(self):
        with patch.object(
            consultas_routes.consultas_cadastro_service,
            "consultar_cep",
            side_effect=ConsultaCadastroError(503, "Provedor indisponível."),
        ):
            with self.assertRaises(HTTPException) as error:
                consultas_routes.consultar_cep(
                    ConsultaCEPInput(cep="01310930"), TENANT
                )
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(error.exception.detail, "Provedor indisponível.")

    def test_partner_sql_errors_are_sanitized_and_rolled_back(self):
        create_db = Mock()
        create_db.execute.side_effect = SQLAlchemyError("secret bind value")
        with self.assertLogs(representante_routes.logger, level="ERROR") as captured:
            with self.assertRaises(HTTPException) as error:
                representante_routes.criar_parceiro(
                    ParceiroCreate(nome="Loja"), create_db, TENANT
                )
        self.assertEqual(error.exception.status_code, 500)
        self.assertEqual(
            error.exception.detail,
            "Erro interno ao acessar cadastro de parceiros.",
        )
        self.assertNotIn("secret bind value", "\n".join(captured.output))
        create_db.rollback.assert_called_once()

        patch_db = Mock()
        patch_db.execute.side_effect = SQLAlchemyError("sensitive update parameters")
        with self.assertRaises(HTTPException) as error:
            representante_routes.atualizar_parceiro(
                8, ParceiroUpdate(nome="Nova loja"), patch_db, TENANT
            )
        self.assertEqual(error.exception.status_code, 500)
        self.assertNotIn("sensitive update parameters", str(error.exception.__cause__))
        patch_db.rollback.assert_called_once()

    def test_partner_commit_error_and_read_errors_return_safe_500(self):
        commit_db = Mock()
        commit_db.execute.return_value.mappings.return_value.one.return_value = _parceiro()
        commit_db.commit.side_effect = SQLAlchemyError("credential-like data")
        with self.assertRaises(HTTPException) as error:
            representante_routes.criar_parceiro(
                ParceiroCreate(nome="Loja"), commit_db, TENANT
            )
        self.assertEqual(error.exception.status_code, 500)
        self.assertEqual(
            error.exception.detail,
            "Erro interno ao acessar cadastro de parceiros.",
        )
        commit_db.rollback.assert_called_once()

        with patch.object(
            representante_routes.representante_service,
            "listar_parceiros",
            side_effect=SQLAlchemyError("sensitive list query"),
        ):
            with self.assertRaises(HTTPException) as error:
                representante_routes.listar_parceiros(False, Mock(), TENANT)
        self.assertEqual(error.exception.status_code, 500)
        self.assertNotIn("sensitive list query", str(error.exception.__cause__))

        with patch.object(
            representante_routes.representante_service,
            "buscar_parceiro",
            side_effect=SQLAlchemyError("sensitive lookup query"),
        ):
            with self.assertRaises(HTTPException) as error:
                representante_routes.buscar_parceiro(8, Mock(), TENANT)
        self.assertEqual(error.exception.status_code, 500)
        self.assertNotIn("sensitive lookup query", str(error.exception.__cause__))


class RevendasMigrationTests(unittest.TestCase):
    def test_migration_is_additive_and_uses_public_preflight(self):
        migration = (
            ROOT / "migrations" / "20261102_revendas_cadastro_completo_v1_up.sql"
        ).read_text(encoding="utf-8")
        expected = (
            "tipo_pessoa", "nome_fantasia", "razao_social", "situacao_cadastral",
            "inscricao_estadual", "inscricao_municipal", "tipo_contribuinte",
            "isento_ie", "telefone_celular", "responsavel", "site", "cep",
            "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
            "vendedor_responsavel_id", "limite_credito", "permitir_exceder_limite",
        )
        self.assertEqual(migration.count("ADD COLUMN IF NOT EXISTS"), 21)
        for column in expected:
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {column}", migration)
        self.assertIn("to_regclass('public.parceiros_comerciais')", migration)
        self.assertNotIn("STAGING", migration)
        self.assertNotIn("UPDATE public.parceiros_comerciais", migration)
        self.assertIn("ck_parceiros_comerciais_cep_v1", migration)
        self.assertIn("cep ~ '^[0-9]{8}$'", migration)
        self.assertIn("UNIQUE (empresa_id, id)", migration)
        self.assertIn("FOREIGN KEY (empresa_id, vendedor_responsavel_id)", migration)
        self.assertIn("REFERENCES public.funcionarios (empresa_id, id)", migration)
        self.assertIn("ON DELETE SET NULL (vendedor_responsavel_id)", migration)
        self.assertIn(
            "ON public.parceiros_comerciais (empresa_id, vendedor_responsavel_id)",
            migration,
        )
        self.assertIn("WHERE vendedor_responsavel_id IS NOT NULL", migration)
        self.assertIn("format_type(a.atttypid, a.atttypmod)", migration)
        self.assertIn("a.attnotnull", migration)
        self.assertIn("expected_default", migration)
        self.assertIn("i.indisvalid", migration)
        self.assertIn("c.convalidated", migration)

    def test_down_warns_about_data_loss_and_drops_only_revendas_columns(self):
        down = (
            ROOT / "migrations" / "20261102_revendas_cadastro_completo_v1_down.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("valores gravados", down)
        self.assertEqual(down.count("DROP COLUMN IF EXISTS"), 21)
        self.assertNotIn("DROP TABLE", down)
        self.assertIn("DROP INDEX IF EXISTS public.ix_parceiros_comerciais_empresa_vendedor_v1", down)
        self.assertIn("DROP CONSTRAINT IF EXISTS ck_parceiros_comerciais_cep_v1", down)
        self.assertIn(
            "DROP CONSTRAINT IF EXISTS uq_funcionarios_empresa_id_revendas_v1",
            down,
        )


class ConsultationInputTests(unittest.TestCase):
    def test_cnpj_checksum_and_cep_format_are_validated(self):
        self.assertEqual(ConsultaCNPJInput(documento="11.222.333/0001-81").documento, "11222333000181")
        with self.assertRaises(ValidationError):
            ConsultaCNPJInput(documento="11222333000182")
        self.assertEqual(ConsultaCEPInput(cep="01310-930").cep, "01310930")
        with self.assertRaises(ValidationError):
            ConsultaCEPInput(cep="12345")

    def test_alphanumeric_cnpj_normalizes_and_validates_ascii_checksum(self):
        # Vector "12ABC34501DE" derives check digits "35" using ASCII-48 values.
        self.assertEqual(
            ConsultaCNPJInput(documento="12.abc.345/01de-35").documento,
            "12ABC34501DE35",
        )
        with self.assertRaises(ValidationError):
            ConsultaCNPJInput(documento="12ABC34501DE36")
        with self.assertRaises(ValidationError):
            ConsultaCNPJInput(documento="AAAAAAAAAAAAAA")

    def test_numeric_and_alphanumeric_cnpj_share_provider_match_normalization(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "cnpj": "12ABC34501DE35",
            "razao_social": "Empresa Exemplo",
        }
        with patch.object(cadastro_adapters.requests, "get", return_value=response) as get:
            result = consultas.consultar_cnpj("12.abc.345/01de-35")
        self.assertEqual(
            get.call_args.args[0],
            "https://brasilapi.com.br/api/cnpj/v1/12ABC34501DE35",
        )
        self.assertEqual(result.dados.razao_social, "Empresa Exemplo")

    def test_client_cannot_inject_provider_url(self):
        with self.assertRaises(ValidationError):
            ConsultaCNPJInput(documento="11222333000181", url="https://attacker.invalid")


if __name__ == "__main__":
    unittest.main()
