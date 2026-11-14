"""Testes unitários isolados de classificação e cadastro fiscal (sem rede ou DB real)."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.fiscal_cadastros import FiscalEmpresaDados, FiscalEmpresaPatch, FiscalProdutoDados, FiscalProdutoPatch
from app.services import fiscal_cadastros
from app.tenant.context import TenantContext


class CadastrosFiscaisTests(unittest.TestCase):
    def test_empresa_inicia_sem_emissao_e_sem_ambiente_producao(self):
        c = FiscalEmpresaDados(crt="1", uf="SP", cep="01001000", serie_nfe=1)
        self.assertEqual(c.ambiente, "HOMOLOGACAO")
        with self.assertRaises(ValidationError):
            FiscalEmpresaDados(ambiente="PRODUCAO")

    def test_empresa_nao_aceita_certificado_senha_ou_url(self):
        for field in ("senha_certificado", "certificado_a1", "url_sefaz", "empresa_id", "emissao_habilitada"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                FiscalEmpresaPatch.model_validate({field: "segredo"})

    def test_referencia_gestaoclick_campos_de_empresa_sem_certificado(self):
        obj = FiscalEmpresaPatch(inscricao_municipal="ISENTO", cnae_principal="4755502",
                                  regime_especial_tributacao="A confirmar",
                                  informacoes_complementares="Texto de teste")
        self.assertEqual(obj.cnae_principal, "4755502")
        self.assertEqual(obj.model_dump(exclude_unset=True)["inscricao_municipal"], "ISENTO")
        for dados in ({"cnae_principal":"123"}, {"informacoes_complementares":"a"*2001}):
            with self.assertRaises(ValidationError):
                FiscalEmpresaPatch.model_validate(dados)

    def test_empresa_campos_validos_e_invalidos(self):
        FiscalEmpresaPatch(uf="SP", municipio_codigo_ibge="3550308", inscricao_estadual="ISENTO", serie_nfe=8)
        for data in ({"serie_nfe": 0}, {"cep": "123"}, {"municipio_codigo_ibge": "abc"}, {"crt": "5"}, {"uf": "SPO"}):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                FiscalEmpresaPatch.model_validate(data)

    def test_produto_codigos_formais_sem_criar_aliquotas(self):
        p = FiscalProdutoDados(ncm="63039200", cfop_padrao_saida="5102", cest="2800100",
                              origem_mercadoria="0", cst_icms="00", csosn="102",
                              cst_ibs_cbs="000", cclass_trib_ibs_cbs="000001")
        self.assertEqual(p.ncm, "63039200")
        self.assertNotIn("aliquota", p.model_dump())
        self.assertNotIn("valor_icms", p.model_dump())

    def test_produto_rejeita_codigos_de_tamanho_errado_e_campos_extras(self):
        for data in ({"ncm": "1234567"}, {"cfop_padrao_saida": "51"}, {"cest": "ABCDE"}, 
                     {"origem_mercadoria": "9"}, {"cclass_trib_ibs_cbs": "12345"},
                     {"empresa_id": 3}, {"aliquota_icms": "18"}):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                FiscalProdutoPatch.model_validate(data)

    def test_patch_parcial_nao_limpa_campos_omitidos(self):
        p = FiscalProdutoPatch(cfop_padrao_saida="5102")
        self.assertEqual(p.model_dump(exclude_unset=True), {"cfop_padrao_saida": "5102"})

    def test_permissao_negada_sem_usuario_ou_papel_admin(self):
        tenant = TenantContext(empresa_id=1)
        db = Mock()
        with self.assertRaises(HTTPException) as ctx:
            fiscal_cadastros.exigir_admin(db, tenant)
        self.assertEqual(ctx.exception.status_code, 403)
        db.query.assert_not_called()
        db2 = Mock()
        db2.query.return_value.filter.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as ctx2:
            fiscal_cadastros.exigir_admin(db2, TenantContext(empresa_id=1, user_id=8))
        self.assertEqual(ctx2.exception.status_code, 403)

    def test_leitura_empresa_nao_vaza_configuracoes_internas(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            id=1, documento="11222333000181", status="ATIVA",
            configuracoes={"perfil_publico": {"nome": "Teste"},
                           "fiscal_nfe": {"uf": "SP", "crt": "3", "senha_certificado": "nao-expor"},
                           "outro_segredo": "nao-expor"})
        payload = fiscal_cadastros.ler_empresa(db, TenantContext(empresa_id=1))
        self.assertEqual(payload["dados"]["uf"], "SP")
        self.assertFalse(payload["emissao_habilitada"])
        self.assertNotIn("senha_certificado", str(payload))
        self.assertNotIn("outro_segredo", str(payload))

    def test_empresa_de_outra_empresa_bloqueada(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            fiscal_cadastros.ler_empresa(db, TenantContext(empresa_id=2))
        self.assertEqual(ctx.exception.status_code, 404)

    def test_produto_de_outra_empresa_bloqueado_antes_de_consultar_fiscal(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            fiscal_cadastros.ler_produto(db, TenantContext(empresa_id=2), 7)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(db.query.call_count, 1)

    def test_leitura_produto_sem_configuracao_retorna_campos_vazios(self):
        db = Mock()
        db.query.return_value.filter.return_value.first.side_effect = [
            SimpleNamespace(id=9, empresa_id=1), None,
        ]
        r = fiscal_cadastros.ler_produto(db, TenantContext(empresa_id=1), 9)
        self.assertFalse(r["configurado"])
        self.assertEqual(r["dados"]["ncm"], None)
        self.assertFalse(r["emissao_habilitada"])


if __name__ == "__main__":
    unittest.main()
