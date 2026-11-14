"""Pré-XML NF-e: regressões sem certificado, transmissão ou dados reais."""
import json
import unittest
from copy import deepcopy

from app.services.fiscal_nfe_mapa_pre_xml import montar_mapa_pre_xml
from app.services.fiscal_nfe_preparacao import analisar_venda_nfe


def sale():
    return {
        "id": 12, "numero": "V-0012", "cliente_id": 2,
        "total": "250.00", "desconto": "0", "total_final": "250.00",
        "total_cliente_final": "350.00",
        "observacao_interna": "NÃO VAZAR comissão/custo secreto",
        "itens": [
            {"tipo_item": "PRODUTO", "produto_id": 100, "codigo_interno": "SKU-100",
             "descricao": "Persiana de Teste", "quantidade": "2.5000",
             "preco_unitario": "100.0000", "subtotal": "250.00", "unidade": "M2"},
        ],
    }


def customer():
    return {
        "nome": "CLIENTE PRIVADO", "documento": "52998224725",
        "cep": "01001000", "logradouro": "Rua Privada",
        "numero": "123", "bairro": "Centro", "cidade": "São Paulo", "estado": "SP",
    }


def taxpayer():
    return {
        "inscricao_estadual": "ISENTO", "crt": "3",
        "ambiente": "HOMOLOGACAO", "serie_nfe": 1,
        "uf": "SP", "municipio_codigo_ibge": "3550308",
        "cidade": "São Paulo", "cep": "01001000", "logradouro": "Rua do Emitente",
        "numero": "1", "bairro": "Centro",
        "informacoes_complementares": "TEXTO PRIVADO NÃO VAZAR",
    }


def inspect_map(pedido=None, destinatario=None, fiscal=None, emitente=None):
    pedido = sale() if pedido is None else pedido
    destinatario = customer() if destinatario is None else destinatario
    fiscal = taxpayer() if fiscal is None else fiscal
    emitente = {"id":1,"documento":"11222333000181","nome":"EMITENTE PRIVADO"} if emitente is None else emitente
    analise = analisar_venda_nfe(pedido,emitente,destinatario)
    return montar_mapa_pre_xml(analise,pedido,emitente,destinatario,fiscal)


class MapaPreXmlTest(unittest.TestCase):
    def test_resumo_grupos_e_nao_emissao(self):
        mapa=inspect_map()
        self.assertEqual(mapa["tipo"],"MAPA_PRE_XML_NFE")
        self.assertEqual(mapa["modelo"],"55")
        self.assertEqual(mapa["estado"],"NAO_APTO_EMISSAO")
        for name in ("xml_gerado","schema_validado","chave_gerada","assinado","transmitido"):
            self.assertFalse(mapa[name])
        self.assertEqual([g["grupo"] for g in mapa["grupos"]],
            ["ide","emit","dest","det","imposto","total","transp","pag","infAdic","Signature"])
        self.assertGreater(mapa["resumo"]["integracoes_pendentes"],0)

    def test_campos_reais_sao_apenas_sinalizados_nao_expostos(self):
        mapa=inspect_map()
        serial=json.dumps(mapa,ensure_ascii=False)
        for private in ("CLIENTE PRIVADO","52998224725","Rua Privada","EMITENTE PRIVADO",
                        "11222333000181","TEXTO PRIVADO NÃO VAZAR",
                        "NÃO VAZAR comissão/custo secreto","350.00","SKU-100"):
            with self.subTest(private=private):
                self.assertNotIn(private,serial)
        self.assertIn("xNome",serial)

    def test_ausencia_de_enderecos_e_fiscal_nao_marca_completo(self):
        mapa=inspect_map(destinatario={}, fiscal={})
        g={grp["grupo"]:grp for grp in mapa["grupos"]}
        for group,field in (("dest","enderDest"),("emit","enderEmit"),("ide","serie")):
            rec=next(c for c in g[group]["campos"] if c["campo_xml"]==field)
            self.assertEqual(rec["situacao"],"PENDENTE")

    def test_itens_nao_produto_sao_excluidos(self):
        pedido=sale()
        pedido["itens"].append({"tipo_item":"SERVICO","descricao":"Lavagem", "quantidade":"1",
                                "subtotal":"1","codigo_interno":"SERVICO-1"})
        mapa=inspect_map(pedido=pedido)
        det=next(g for g in mapa["grupos"] if g["grupo"]=="det")
        self.assertEqual(sum(c["campo_xml"]=="det[]"
                             for c in det["campos"]),1)
        self.assertFalse(any("det[2]" in c["campo_xml"] for c in det["campos"]))

    def test_quantidade_quatro_casas_nao_e_arredondada(self):
        pedido=sale()
        pedido["itens"][0]["quantidade"]="0.0001"
        mapa=inspect_map(pedido=pedido)
        det=next(g for g in mapa["grupos"] if g["grupo"]=="det")
        q=next(c for c in det["campos"] if c["campo_xml"]=="det[1]/prod/qCom")
        self.assertEqual(q["situacao"],"INFORMADO")
        # Não grava quantidade, apenas sinaliza presença/positividade.
        self.assertNotIn("0.0001",json.dumps(mapa))

    def test_prevalidacao_nao_arredonda_quantidade_positiva(self):
        pedido = sale()
        pedido["itens"][0]["quantidade"] = "0.0001"
        r = analisar_venda_nfe(pedido, {"id":1,"documento":"11222333000181"}, customer())
        self.assertNotIn("QUANTIDADE_INVALIDA", {p["codigo"] for p in r["pendencias"]})
        pedido["itens"][0]["quantidade"] = "0.00001"
        r = analisar_venda_nfe(pedido, {"id":1,"documento":"11222333000181"}, customer())
        self.assertIn("QUANTIDADE_INVALIDA", {p["codigo"] for p in r["pendencias"]})

    def test_numeros_invalidos_bloqueiam_itens(self):
        pedido=sale()
        pedido["itens"][0]["quantidade"]="NaN"
        pedido["itens"][0]["preco_unitario"]="-1"
        mapa=inspect_map(pedido=pedido)
        det=next(g for g in mapa["grupos"] if g["grupo"]=="det")
        for key in ("det[1]/prod/qCom","det[1]/prod/vUnCom"):
            rec=next(c for c in det["campos"] if c["campo_xml"]==key)
            self.assertEqual(rec["situacao"],"PENDENTE")

    def test_numero_comercial_nao_virou_numero_fiscal(self):
        mapa=inspect_map()
        ide=next(g for g in mapa["grupos"] if g["grupo"]=="ide")
        num=next(c for c in ide["campos"] if c["campo_xml"]=="nNF")
        self.assertEqual(num["situacao"],"INTEGRACAO_PENDENTE")
        self.assertNotIn("V-0012",json.dumps(mapa))

    def test_nao_existe_chave_xml_ou_documento_no_retorno(self):
        mapa=inspect_map()
        for field in ("xml","xml_nfe","chave_acesso","protocolo","danfe","cpf","cnpj","valor"):
            self.assertNotIn(field,mapa)


if __name__=="__main__":
    unittest.main()
