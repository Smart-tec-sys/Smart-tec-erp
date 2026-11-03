import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.routes import consultas_cadastro as routes
from app.schemas.consultas_cadastro import ConsultaCNPJInput
from app.services import consultas_cadastro_adapters as adapters
from app.services import consultas_cadastro_service as service


CNPJ = "11222333000181"


def resposta(payload, status=200):
    response = Mock(status_code=status)
    response.json.return_value = payload
    return response


class EnriquecimentoTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "SMARTTEC_CNPJ_CONSULTA_PROVIDER": "brasilapi",
            "SMARTTEC_CNPJ_CONTATOS_FALLBACK": "cnpja",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.limite = patch.object(adapters, "_LIMITE_CNPJA", adapters.LimiteCnpja())
        self.limite.start()
        self.addCleanup(self.limite.stop)
        self.principal = {"cnpj": CNPJ, "nome_fantasia": "", "email": None, "ddd_telefone_1": ""}
        self.fallback = {
            "taxId": CNPJ,
            "alias": "Nao deve preencher fantasia",
            "emails": [{"address": " CONTATO@EXAMPLE.TEST "}],
            "phones": [{"type": "MOBILE", "area": "11", "number": "33334444"}],
            "address": {"street": "Nao deve enriquecer endereco"},
        }

    def consultar(self, principal=None, fallback=None):
        with patch.object(adapters.requests, "get", side_effect=[
            resposta(self.principal if principal is None else principal),
            resposta(self.fallback if fallback is None else fallback),
        ]) as get:
            result = service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
        return result, get

    def test_completa_contatos_sem_fantasia_celular_ou_endereco(self):
        with self.assertLogs(service.__name__, level="INFO") as logs:
            result, get = self.consultar()
        self.assertEqual(result.dados.email, "contato@example.test")
        self.assertEqual(result.dados.telefone_comercial, "1133334444")
        self.assertIsNone(result.dados.nome_fantasia)
        self.assertIsNone(result.dados.logradouro)
        self.assertEqual(result.fontes_campos, {"email": "cnpja", "telefone_comercial": "cnpja"})
        self.assertIsNone(result.avisos)
        self.assertNotIn(CNPJ, " ".join(logs.output))
        self.assertNotIn("contato@", " ".join(logs.output))
        self.assertNotIn("1133334444", " ".join(logs.output))
        get.assert_called_with(
            "https://open.cnpja.com/office/" + CNPJ,
            timeout=(3.05, 10), allow_redirects=False,
        )

    def test_preserva_campo_principal(self):
        result, _ = self.consultar({**self.principal, "email": "principal@example.test"})
        self.assertEqual(result.dados.email, "principal@example.test")
        self.assertEqual(result.fontes_campos["email"], "brasilapi")
        self.assertEqual(result.fontes_campos["telefone_comercial"], "cnpja")
        result, _ = self.consultar({**self.principal, "ddd_telefone_1": "11999999999"})
        self.assertEqual(result.dados.telefone_comercial, "11999999999")

    def test_nao_consulta_quando_completo_ou_sem_opt_in(self):
        self.assertFalse(ConsultaCNPJInput(documento=CNPJ).enriquecer_contatos)
        for opt_in, payload in (
            (False, self.principal),
            (True, {**self.principal, "email": "a@example.test", "ddd_telefone_1": "1133334444"}),
        ):
            with patch.object(adapters.requests, "get", return_value=resposta(payload)) as get:
                result = service.consultar_cnpj(CNPJ, enriquecer_contatos=opt_in)
            self.assertEqual(get.call_count, 1)
            self.assertIsNone(result.fontes_campos)

    def test_incompleto_sinaliza_sem_inventar(self):
        result, _ = self.consultar(fallback={"taxId": CNPJ, "emails": [], "phones": []})
        self.assertIsNone(result.dados.email)
        self.assertIsNone(result.dados.telefone_comercial)
        self.assertTrue(result.avisos)
        result, _ = self.consultar(fallback={"taxId": CNPJ, "emails": [{"address": "a@example.test"}]})
        self.assertEqual(result.dados.email, "a@example.test")
        self.assertIsNone(result.dados.telefone_comercial)
        self.assertTrue(result.avisos)

    def test_divergentes_e_malformados_nao_sao_aplicados(self):
        for payload in (
            {**self.fallback, "taxId": "00000000000000"},
            {**self.fallback, "emails": {}},
            {**self.fallback, "phones": {}},
            {**self.fallback, "phones": [{"area": "11", "number": 33334444}]},
            {**self.fallback, "emails": [{"address": "invalido"}]},
            {**self.fallback, "emails": [{"address": "a@example.test"}, {"address": "b@example.test"}]},
        ):
            with self.subTest(payload=payload), patch.object(adapters, "_LIMITE_CNPJA", adapters.LimiteCnpja()):
                result, _ = self.consultar(fallback=payload)
                self.assertIsNone(result.dados.email)
                self.assertIsNone(result.dados.telefone_comercial)
                self.assertTrue(result.avisos)

    def test_falhas_preservam_principal_com_aviso(self):
        for failure in (
            adapters.requests.exceptions.Timeout(),
            adapters.requests.exceptions.ConnectionError(),
            resposta({}, 404), resposta({}, 429), resposta({}, 503),
        ):
            with self.subTest(failure=failure), patch.object(adapters, "_LIMITE_CNPJA", adapters.LimiteCnpja()):
                with patch.object(adapters.requests, "get", side_effect=[
                    resposta({**self.principal, "email": "principal@example.test"}), failure,
                ]):
                    result = service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
                self.assertEqual(result.dados.email, "principal@example.test")
                self.assertIsNone(result.dados.telefone_comercial)
                self.assertTrue(result.avisos)

    def test_indisponibilidade_principal_recupera_contatos_com_opt_in(self):
        for failure in (
            resposta({}, 429), resposta({}, 503), resposta({}, 500),
            adapters.requests.exceptions.Timeout(),
            adapters.requests.exceptions.ConnectionError(),
        ):
            with self.subTest(failure=failure), patch.object(adapters, "_LIMITE_CNPJA", adapters.LimiteCnpja()):
                with patch.object(adapters.requests, "get", side_effect=[
                    failure, resposta(self.fallback),
                ]) as get, self.assertLogs(service.__name__, level="INFO") as logs:
                    result = service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
                self.assertEqual(get.call_count, 2)
                self.assertEqual(result.fonte, "cnpja")
                self.assertEqual(result.dados.email, "contato@example.test")
                self.assertEqual(result.dados.telefone_comercial, "1133334444")
                self.assertIsNone(result.dados.nome_fantasia)
                self.assertIsNone(result.dados.razao_social)
                self.assertTrue(result.avisos)
                self.assertNotIn(CNPJ, " ".join(logs.output))
                self.assertNotIn("contato@example.test", " ".join(logs.output))

    def test_falha_principal_nao_aciona_fallback_sem_opt_in_ou_nao_temporaria(self):
        for opt_in, status in ((False, 429), (False, 503), (True, 404), (True, 400)):
            with self.subTest(opt_in=opt_in, status=status):
                with patch.object(adapters.requests, "get", return_value=resposta({}, status)) as get:
                    with self.assertRaises(adapters.ConsultaCadastroError):
                        service.consultar_cnpj(CNPJ, enriquecer_contatos=opt_in)
                self.assertEqual(get.call_count, 1)

    def test_duas_fontes_falham_rota_informa_cadastro_manual(self):
        for alternative in (
            resposta({}, 503), resposta({}, 429),
            adapters.requests.exceptions.Timeout(),
            resposta({**self.fallback, "taxId": "00000000000000"}),
            resposta({"taxId": CNPJ, "emails": [], "phones": []}),
        ):
            with self.subTest(alternative=alternative), patch.object(adapters, "_LIMITE_CNPJA", adapters.LimiteCnpja()):
                with patch.object(adapters.requests, "get", side_effect=[
                    resposta({}, 429), alternative,
                ]) as get:
                    with self.assertRaises(HTTPException) as error:
                        routes.consultar_cnpj(
                            ConsultaCNPJInput(documento=CNPJ, enriquecer_contatos=True), Mock()
                        )
                self.assertIn(error.exception.status_code, (429, 502, 503))
                self.assertIn("manualmente", error.exception.detail)
                self.assertNotIn("00000000000000", error.exception.detail)
                self.assertEqual(get.call_count, 2)

    def test_recuperacao_principal_respeita_limite_e_bloqueio(self):
        with patch.object(adapters.time, "monotonic", return_value=100):
            for _ in range(5):
                adapters._LIMITE_CNPJA.reservar()
            with patch.object(adapters.requests, "get", return_value=resposta({}, 503)) as get:
                with self.assertRaises(adapters.ConsultaCadastroError) as error:
                    service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
            self.assertEqual(error.exception.status_code, 429)
            self.assertEqual(get.call_count, 1)
        with patch.object(adapters, "_LIMITE_CNPJA", adapters.LimiteCnpja()):
            with patch.object(adapters.time, "monotonic", return_value=100):
                adapters._LIMITE_CNPJA.bloquear()
                with patch.object(adapters.requests, "get", return_value=resposta({}, 429)) as get:
                    with self.assertRaises(adapters.ConsultaCadastroError):
                        service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
                self.assertEqual(get.call_count, 1)

    def test_alternativa_desabilitada_apos_falha_principal(self):
        with patch.dict(os.environ, {"SMARTTEC_CNPJ_CONTATOS_FALLBACK": "off"}):
            with patch.object(adapters.requests, "get", return_value=resposta({}, 503)) as get:
                with self.assertRaises(adapters.ConsultaCadastroError) as error:
                    service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
        self.assertIn("desabilitada", error.exception.detail)
        self.assertEqual(get.call_count, 1)

    def test_limite_exato_e_reabertura(self):
        with patch.object(adapters.time, "monotonic", return_value=100):
            for _ in range(5):
                self.consultar()
            result, get = self.consultar()
            self.assertEqual(get.call_count, 1)
            self.assertTrue(result.avisos)
        with patch.object(adapters.time, "monotonic", return_value=159.999):
            with self.assertRaises(adapters.ConsultaCadastroError):
                adapters._LIMITE_CNPJA.reservar()
        with patch.object(adapters.time, "monotonic", return_value=160):
            adapters._LIMITE_CNPJA.reservar()

    def test_limite_concorrente(self):
        def reservar(_):
            try:
                adapters._LIMITE_CNPJA.reservar()
                return True
            except adapters.ConsultaCadastroError:
                return False
        with patch.object(adapters.time, "monotonic", return_value=100):
            with ThreadPoolExecutor(max_workers=10) as pool:
                self.assertEqual(sum(pool.map(reservar, range(20))), 5)

    def test_429_bloqueia_novas_consultas(self):
        with patch.object(adapters.time, "monotonic", return_value=100):
            with patch.object(adapters.requests, "get", side_effect=[
                resposta(self.principal), resposta({}, 429),
            ]):
                result = service.consultar_cnpj(CNPJ, enriquecer_contatos=True)
            self.assertTrue(result.avisos)
            result, get = self.consultar()
            self.assertEqual(get.call_count, 1)
        with patch.object(adapters.time, "monotonic", return_value=160):
            adapters._LIMITE_CNPJA.reservar()

    def test_desabilitado_e_configuracao_invalida(self):
        with patch.dict(os.environ, {"SMARTTEC_CNPJ_CONTATOS_FALLBACK": "off"}):
            result, get = self.consultar()
            self.assertEqual(get.call_count, 1)
            self.assertTrue(result.avisos)
        with patch.dict(os.environ, {"SMARTTEC_CNPJ_CONTATOS_FALLBACK": "url-invalida"}):
            with self.assertRaises(adapters.ConsultaCadastroError):
                self.consultar()

    def test_rota_encaminha_opt_in_e_rejeita_tipo_invalido(self):
        with patch.object(service, "consultar_cnpj", return_value=Mock()) as consulta:
            routes.consultar_cnpj(
                ConsultaCNPJInput(documento=CNPJ, enriquecer_contatos=True), Mock()
            )
        consulta.assert_called_once_with(CNPJ, enriquecer_contatos=True)
        with self.assertRaises(ValidationError):
            ConsultaCNPJInput(documento=CNPJ, enriquecer_contatos="false")
