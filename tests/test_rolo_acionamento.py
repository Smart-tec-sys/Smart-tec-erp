"""Acionamentos no mesmo acabado; referências/faixas sintéticas em SQLite em memória."""
import copy
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models.empresa import EmpresaDB
from app.models.orcamento import OrcamentoItemDB
from app.models.pedido import PedidoItemDB
from app.models.produto import ProdutoDB
from app.schemas.orcamento import OrcamentoInput
from app.schemas.pedido import PedidoCreate
from app.routes.orcamento import router
from app.services.composicao_comercial import calcular_itens
from app.services.rolo_receita import listar_acessorios_comando_rolo, listar_motores_rolo, simular_rolo_catalogo
from app.services.rolo_simulacao import RoloSimulacaoInput
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant
from test_rolo_picasso import picasso, ativar, acabado  # noqa: F401


def entrada(p, **campos):
    if campos.get("acionamento", "motorizado") == "motorizado":
        largura = campos.get("largura", 1.3)
        faixas = getattr(p, "_faixas_teste", [])
        faixa = next((f for f in faixas if f["largura_min_m"] < largura <= f["largura_max_m"]), None)
        bitola = f"{faixa['diametro_mm']}mm" if faixa else ""
        if "motor_produto_id" not in campos:
            campos["motor_produto_id"] = getattr(p, "_motores_teste", {}).get(bitola)
        if "kit_produto_id" not in campos:
            campos["kit_produto_id"] = getattr(p, "_kits_teste", {}).get(bitola)
    return RoloSimulacaoInput(**(dict(produto_id=p.id, largura=1.3, altura=2,
                                    quantidade=1, cor="AMENDOA", acionamento="motorizado") | campos))


def _insumo(db, codigo, unidade, diametro, custo):
    row = ProdutoDB(empresa_id=1, nome=f"Insumo sintético {codigo}", codigo_interno=codigo,
                    tipo_produto="Componente", unidade_venda=unidade,
                    custo_final=custo, valor_custo=custo, situacao="Ativo")
    db.add(row)
    db.flush()
    return {"produto_id": row.id, "codigo_interno": codigo, "unidade_tecnica": unidade,
            "preco_compra": custo, "ipi_percentual": None, "unidades_por_compra": 1,
            "origem": "Dado exclusivamente sintético de teste; não aplicar no catálogo",
            "base_preco": "CUSTO_CADASTRADO", "diametro_mm": diametro}


def _salvar_config(db, p, receita, chave=None):
    empresa = db.get(EmpresaDB, 1)
    cfg = copy.deepcopy(empresa.configuracoes)
    copia = copy.deepcopy(receita)
    if ":manual" not in (chave or ""):
        if not copia.get("conjuntos_motor"):
            copia["conjuntos_motor"] = [
                {"motor": motor, "torque_nm": 6, "tecnologia": "RF",
                 "tubos": {bitola: copia["tubos"][bitola]},
                 "kits_motor": {bitola: copia["kits_motor"][bitola]},
                 "faixas_tubo": [faixa for faixa in copia["faixas_tubo"]
                                  if f"{faixa['diametro_mm']}mm" == bitola]}
                for bitola, motor in copia["motores"].items()
                if bitola in copia["tubos"] and bitola in copia["kits_motor"]
                and any(f"{faixa['diametro_mm']}mm" == bitola for faixa in copia["faixas_tubo"])
            ]
        for conjunto in copia["conjuntos_motor"]:
            conjunto.update({
                "capacidade_kg": 20, "peso_barra_kg": 1,
                "peso_estimado_kg_m2": 0.5,
                "origem_carga": "Dados sintéticos exclusivos desta fixture",
            })
        p._motores_teste = {bitola: motor["produto_id"] for bitola, motor in copia["motores"].items()}
        p._kits_teste = {bitola: kit["produto_id"] for bitola, kit in copia["kits_motor"].items()}
        for conjunto in copia["conjuntos_motor"]:
            p._kits_teste.update({bitola: kit["produto_id"] for bitola, kit in conjunto["kits_motor"].items()})
        p._faixas_teste = copia["faixas_tubo"]
    cfg["receitas_rolo_v1"][chave or f"{p.id}:motorizado"] = copia
    empresa.configuracoes = cfg
    db.flush()


@pytest.fixture
def configurada(picasso):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db)
    manual = simular_rolo_catalogo(db, p, entrada(p, acionamento="manual"), 1)
    original = db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)]
    receita = copy.deepcopy(original)
    receita["componentes"] = {k: v for k, v in receita["componentes"].items()
                             if k not in {"corrente", "emenda_corrente"}}
    receita["comandos"] = {}
    receita["tubos"], receita["motores"], receita["kits_motor"] = {}, {}, {}
    receita["faixas_tubo"] = []
    # Limites fictícios para exercitar seleção; nenhuma capacidade real é inferida.
    for diametro, minimo, maximo in [(41, 0, 1), (56, 1, 1.5), (70, 1.5, 2.5)]:
        bitola = f"{diametro}mm"
        receita["tubos"][bitola] = _insumo(db, f"TEST-TUBO-{diametro}", "ML", diametro, 10)
        receita["motores"][bitola] = _insumo(db, f"TEST-MOTOR-{diametro}", "UN", diametro, 100)
        receita["kits_motor"][bitola] = _insumo(db, f"TEST-KIT-{diametro}", "KIT", diametro, 12)
        receita["faixas_tubo"].append({"diametro_mm": diametro, "largura_min_m": minimo,
                                       "largura_max_m": maximo, "altura_max_m": 3,
                                       "origem": "Faixa sintética de teste, sem validade comercial"})
    _salvar_config(db, p, receita)
    return db, p, receita, manual


@pytest.mark.parametrize("largura,bitola", [(0.9, "41mm"), (1, "41mm"), (1.3, "56mm"),
                                          (1.5, "56mm"), (1.9, "70mm")])
def test_mesmo_id_motor_e_bitola_da_faixa_aprovada(configurada, largura, bitola):
    db, p, _, _ = configurada
    antes = (p.id, p.nome, p.cor, p.custo_final, p.valor_custo, p.valor_venda)
    with patch.object(db, "commit", side_effect=AssertionError("Simulação não persiste")):
        result = simular_rolo_catalogo(db, p, entrada(p, largura=largura), 1)
    assert result["bitola_tecnica"] == bitola
    assert result["acionamento_permitido"] == "motorizado"
    assert result["preco_disponivel"]
    assert len(result["fabricacao_por_peca"]["componentes"]) == 9
    categorias = {c["categoria"] for c in result["fabricacao_por_peca"]["componentes"]}
    assert {"Motor", "Acessórios do motor"} <= categorias
    assert not {"Comando", "Corrente", "Emenda corrente"} & categorias
    assert (p.id, p.nome, p.cor, p.custo_final, p.valor_custo, p.valor_venda) == antes


def test_troca_manual_motor_manual_preserva_picasso(configurada):
    db, p, _, manual = configurada
    motor = simular_rolo_catalogo(db, p, entrada(p), 1)
    depois = simular_rolo_catalogo(db, p, entrada(p, acionamento="manual"), 1)
    assert depois == manual
    assert motor["preco_unitario"] != manual["preco_unitario"]
    assert motor["custo_tecnico"] != manual["custo_tecnico"]
    partes_manuais = manual["fabricacao_por_peca"]["componentes"]
    partes_motorizadas = motor["fabricacao_por_peca"]["componentes"]
    itens_removidos = sum(
        item["custo_total"] for item in partes_manuais
        if item["categoria"] in {"Tubo", "Corrente", "Emenda corrente", "Comando"}
    )
    itens_motorizados = sum(
        item["custo_total"] for item in partes_motorizadas
        if item["categoria"] in {"Tubo", "Motor", "Acessórios do motor"}
    )
    assert motor["custo_tecnico"] == pytest.approx(
        manual["custo_tecnico"] - itens_removidos + itens_motorizados,
    )
    assert len(partes_motorizadas) == 9
    assert not {
        "Comando", "Corrente", "Emenda corrente", "Suporte do motor",
        "Adaptador do motor", "Ponteira do tubo",
    } & {item["categoria"] for item in partes_motorizadas}


def test_tubo_38_manual_pode_ser_mantido_em_motor_com_kit_e_faixa_aprovados(configurada):
    db, p, receita, _ = configurada
    manual = simular_rolo_catalogo(db, p, entrada(p, largura=1.9, acionamento="manual"), 1)
    original = db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)]
    receita["tubos"]["38mm"] = copy.deepcopy(original["tubos"]["38mm"])
    receita["motores"]["38mm"] = _insumo(db, "TEST-MOTOR-38", "UN", 38, 100)
    receita["kits_motor"]["38mm"] = _insumo(db, "TEST-KIT-38", "KIT", 38, 12)
    receita["faixas_tubo"] = [{"diametro_mm": 38, "largura_min_m": 1.8, "largura_max_m": 2.0,
                               "altura_max_m": 3, "origem": "Faixa sintética exclusivamente de teste"}]
    _salvar_config(db, p, receita)
    motorizada = simular_rolo_catalogo(db, p, entrada(p, largura=1.9), 1)
    assert manual["bitola_tecnica"] == motorizada["bitola_tecnica"] == "38mm"
    assert manual["componentes_tecnicos"]["tubo"]["produto_codigo"] == motorizada["componentes_tecnicos"]["tubo"]["produto_codigo"]
    categorias = [c["categoria"] for c in motorizada["fabricacao_por_peca"]["componentes"]]
    assert categorias.count("Motor") == categorias.count("Acessórios do motor") == 1
    assert not {"Comando", "Corrente", "Emenda corrente"} & set(categorias)
    assert not {"Suporte do motor", "Adaptador do motor", "Ponteira do tubo"} & set(categorias)
    assert simular_rolo_catalogo(db, p, entrada(p, largura=1.9, acionamento="manual"), 1) == manual


def test_motor_38_sem_kit_aprovado_nao_reaproveita_tubo_por_suposição(configurada):
    db, p, receita, _ = configurada
    receita["faixas_tubo"] = [{"diametro_mm": 38, "largura_min_m": 0, "largura_max_m": 2,
                               "altura_max_m": 3, "origem": "Faixa sintética exclusivamente de teste"}]
    receita["tubos"]["38mm"] = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)]["tubos"]["38mm"])
    receita["motores"]["38mm"] = _insumo(db, "TEST-MOTOR-38", "UN", 38, 100)
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError, match="faltam dados técnicos cadastrados"):
        simular_rolo_catalogo(db, p, entrada(
            p, largura=1.9, kit_produto_id=receita["kits_motor"]["70mm"]["produto_id"],
        ), 1)


def test_motor_38_com_kit_de_outra_bitola_e_bloqueado(configurada):
    db, p, receita, _ = configurada
    receita["faixas_tubo"] = [{"diametro_mm": 38, "largura_min_m": 0, "largura_max_m": 2,
                               "altura_max_m": 3, "origem": "Faixa sintética exclusivamente de teste"}]
    receita["tubos"]["38mm"] = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)]["tubos"]["38mm"])
    receita["motores"]["38mm"] = _insumo(db, "TEST-MOTOR-38", "UN", 38, 100)
    receita["kits_motor"]["38mm"] = _insumo(db, "TEST-KIT-INCOMPATIVEL", "KIT", 41, 12)
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError, match="Receita Rol"):
        simular_rolo_catalogo(db, p, entrada(p, largura=1.9), 1)


def test_motor_selecionado_reutiliza_tubo_manual_38(configurada):
    db, p, receita, _ = configurada
    tubo = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)]["tubos"]["38mm"])
    motor = _insumo(db, "TEST-MOTOR-SELECIONADO-38", "UN", 38, 100)
    kit = _insumo(db, "TEST-KIT-SELECIONADO-38", "KIT", 38, 12)
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "CONTATO_SECO",
        "tubos": {"38mm": tubo}, "kits_motor": {"38mm": kit},
        "faixas_tubo": [{"diametro_mm": 38, "largura_min_m": 1.8, "largura_max_m": 2,
                          "altura_max_m": 3, "origem": "Faixa sintética exclusivamente de teste"}]}]
    receita["tubos"]["38mm"] = tubo
    receita["faixas_tubo"] = copy.deepcopy(receita["conjuntos_motor"][0]["faixas_tubo"])
    _salvar_config(db, p, receita)
    manual = simular_rolo_catalogo(db, p, entrada(p, largura=1.9, acionamento="manual"), 1)
    resultado = simular_rolo_catalogo(db, p, entrada(p, largura=1.9, motor_produto_id=motor["produto_id"]), 1)
    assert manual["componentes_tecnicos"]["tubo"]["produto_codigo"] == resultado["componentes_tecnicos"]["tubo"]["produto_codigo"]
    assert resultado["componentes_tecnicos"]["motor"]["tecnologia"] == "CONTATO_SECO"
    assert all("controle" not in c["nome"].casefold() for c in resultado["fabricacao_por_peca"]["componentes"])


def test_faixas_sobrepostas_mantem_tubo_38_manual_exatamente_igual(configurada):
    db, p, receita, _ = configurada
    tubo_manual = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)]["tubos"]["38mm"])
    motor = _insumo(db, "TEST-MOTOR-MULTITUBO", "UN", 38, 100)
    motor["diametro_mm"] = None
    kit_38 = _insumo(db, "TEST-KIT-MULTITUBO-38", "KIT", 38, 12)
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "RF",
        "tubos": {"38mm": tubo_manual, "70mm": receita["tubos"]["70mm"]},
        "kits_motor": {"38mm": kit_38, "70mm": receita["kits_motor"]["70mm"]},
        "faixas_tubo": [
            {"diametro_mm": 38, "largura_min_m": 1.8, "largura_max_m": 2, "altura_max_m": 3,
             "origem": "Faixa sintética exclusivamente de teste"},
            {"diametro_mm": 70, "largura_min_m": 1.8, "largura_max_m": 2, "altura_max_m": 3,
             "origem": "Faixa sintética exclusivamente de teste"},
        ]}]
    receita["tubos"]["38mm"] = tubo_manual
    receita["faixas_tubo"] = [copy.deepcopy(receita["conjuntos_motor"][0]["faixas_tubo"][0])]
    _salvar_config(db, p, receita)
    resultado = simular_rolo_catalogo(db, p, entrada(p, largura=1.9, motor_produto_id=motor["produto_id"]), 1)
    assert resultado["bitola_tecnica"] == "38mm"
    assert resultado["componentes_tecnicos"]["tubo"]["produto_codigo"] == tubo_manual["codigo_interno"]
    receita["conjuntos_motor"][0]["tubos"]["38mm"] = _insumo(db, "TEST-OUTRO-TUBO-38", "ML", 38, 10)
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError, match="Motor sem tubo"):
        simular_rolo_catalogo(db, p, entrada(p, largura=1.9, motor_produto_id=motor["produto_id"]), 1)
    receita["conjuntos_motor"][0]["tubos"]["38mm"] = tubo_manual
    receita["conjuntos_motor"][0]["kits_motor"]["38mm"]["diametro_mm"] = 41
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p, largura=1.9, motor_produto_id=motor["produto_id"]), 1)


def test_familia_41_43_exige_fonte_para_kit_de_outra_bitola(configurada):
    db, p, receita, _ = configurada
    tubo = _insumo(db, "TEST-TUBO-43", "ML", 43, 10)
    motor = _insumo(db, "TEST-MOTOR-43", "UN", 43, 100)
    kit = _insumo(db, "TEST-KIT-41-PARA-43", "KIT", 41, 12)
    faixa = {"diametro_mm": 43, "largura_min_m": 1.2, "largura_max_m": 1.4,
             "altura_max_m": 3, "origem": "Limite sintético exclusivamente de teste"}
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "RF",
        "tubos": {"43mm": tubo}, "kits_motor": {"43mm": kit}, "faixas_tubo": [faixa]}]
    receita["tubos"]["43mm"] = tubo
    receita["faixas_tubo"] = [faixa]
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p, largura=1.3, motor_produto_id=motor["produto_id"]), 1)

    receita["conjuntos_motor"][0]["compatibilidades"] = {
        "43mm": "Vínculo técnico sintético de teste; sem validade fora da fixture"
    }
    _salvar_config(db, p, receita)
    result = simular_rolo_catalogo(db, p, entrada(p, largura=1.3, motor_produto_id=motor["produto_id"]), 1)
    assert result["bitola_tecnica"] == "43mm"
    assert result["componentes_tecnicos"]["tubo"]["produto_codigo"] == tubo["codigo_interno"]


def test_seletor_lista_somente_motores_compativeis_com_as_medidas(configurada):
    db, p, receita, _ = configurada
    receita["conjuntos_motor"] = [
        {"motor": receita["motores"][bitola], "torque_nm": 6, "tecnologia": "RF",
         "tubos": {bitola: receita["tubos"][bitola]},
         "kits_motor": {bitola: receita["kits_motor"][bitola]},
         "faixas_tubo": [faixa]}
        for bitola, faixa in zip(("41mm", "56mm", "70mm"), receita["faixas_tubo"])
    ]
    _salvar_config(db, p, receita)
    pequena = listar_motores_rolo(db, p, entrada(p, largura=0.9), 1)
    media = listar_motores_rolo(db, p, entrada(p, largura=1.3), 1)
    assert [item["produto_id"] for item in pequena] == [receita["motores"]["41mm"]["produto_id"]]
    assert [item["produto_id"] for item in media] == [receita["motores"]["56mm"]["produto_id"]]


def test_endpoint_motores_usa_tenant_e_nao_grava(configurada):
    db, p, receita, _ = configurada
    motor = receita["motores"]["56mm"]
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "RF",
        "tubos": {"56mm": receita["tubos"]["56mm"]}, "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
        "faixas_tubo": [receita["faixas_tubo"][1]]}]
    _salvar_config(db, p, receita)
    app = FastAPI()
    app.include_router(router, prefix="/orcamentos")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1, user_id=1)
    payload = {"produto_id": p.id, "largura": 1.3, "altura": 2, "quantidade": 1,
               "cor": "AMENDOA", "acionamento": "motorizado"}
    with TestClient(app) as client, patch.object(db, "commit", side_effect=AssertionError("Não persistir consulta")):
        resposta = client.post("/orcamentos/motores-rolo", json=payload)
        assert resposta.status_code == 200
        assert resposta.json()[0]["produto_id"] == motor["produto_id"]
        app.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=2, user_id=1)
        assert client.post("/orcamentos/motores-rolo", json=payload).status_code == 404


@pytest.mark.parametrize("schema,item_model", [(OrcamentoInput, OrcamentoItemDB), (PedidoCreate, PedidoItemDB)])
def test_controle_compartilhado_e_cobrado_por_unidade_e_validado(schema, item_model, configurada):
    db, p, receita, _ = configurada
    motor = receita["motores"]["56mm"]
    controle = _insumo(db, "TEST-CONTROLE-RF", "UN", 56, 20)
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "WIFI_RF",
        "tubos": {"56mm": receita["tubos"]["56mm"]}, "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
        "faixas_tubo": [receita["faixas_tubo"][1]],
        "acessorios_comando": [{"insumo": controle, "tipo": "CONTROLE_RF", "canais": 6}]}]
    _salvar_config(db, p, receita)
    dados = entrada(p, motor_produto_id=motor["produto_id"])
    assert listar_acessorios_comando_rolo(db, [dados, dados], 1)[0]["produto_id"] == controle["produto_id"]
    persiana = {"produto_id": p.id, "descricao": p.nome, "unidade": "M2", "largura": 1.3,
        "altura": 2, "quantidade": 1, "cor": "AMENDOA", "ambiente": "Sala",
        "acionamento": "motorizado", "preco_unitario": 0,
        "dados_tecnicos": {"rolo": {"motor_produto_id": motor["produto_id"],
                                    "kit_produto_id": dados.kit_produto_id}}}
    acessorio = {"produto_id": controle["produto_id"], "descricao": "Controle", "unidade": "UN",
        "ambiente": " SALA ", "quantidade": 1, "preco_unitario": 0,
        "modelo_tecnico": "ROLO", "dados_tecnicos": {"acessorio_rolo": {"vinculo": "AMBIENTE"}}}
    documento = SimpleNamespace(itens=[])
    calcular_itens(db, documento, schema(cliente_id=1, itens=[persiana, persiana, acessorio]), 1, item_model)
    assert documento.itens[2].subtotal == Decimal("40.00")
    assert documento.itens[2].quantidade == 1
    assert documento.total == documento.itens[0].subtotal + documento.itens[1].subtotal + Decimal("40.00")
    acessorio["quantidade"] = 2
    calcular_itens(db, documento, schema(cliente_id=1, itens=[persiana, persiana, acessorio]), 1, item_model)
    assert documento.itens[2].subtotal == Decimal("80.00")
    acessorio["ambiente"] = "Quarto"
    itens_anteriores = list(documento.itens)
    with pytest.raises(ValueError, match="ambiente"):
        calcular_itens(db, documento, schema(cliente_id=1, itens=[persiana, acessorio]), 1, item_model)
    assert documento.itens == itens_anteriores
    acessorio["ambiente"] = "Sala"
    outro = dict(persiana, dados_tecnicos={"rolo": {"motor_produto_id": 999999}})
    with pytest.raises(ValueError):
        calcular_itens(db, documento, schema(cliente_id=1, itens=[persiana, outro, acessorio]), 1, item_model)
    acessorio["quantidade"] = 1.5
    with pytest.raises(ValueError, match="quantidade inteira"):
        calcular_itens(db, documento, schema(cliente_id=1, itens=[persiana, acessorio]), 1, item_model)


def test_contato_seco_nao_aceita_controle_rf(configurada):
    db, p, receita, _ = configurada
    motor = receita["motores"]["56mm"]
    controle = _insumo(db, "TEST-RF-INCOMPATIVEL", "UN", 56, 20)
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "CONTATO_SECO",
        "tubos": {"56mm": receita["tubos"]["56mm"]}, "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
        "faixas_tubo": [receita["faixas_tubo"][1]],
        "acessorios_comando": [{"insumo": controle, "tipo": "CONTROLE_RF", "canais": 1}]}]
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError, match="Receita Rol"):
        simular_rolo_catalogo(db, p, entrada(p, motor_produto_id=motor["produto_id"]), 1)


@pytest.mark.parametrize("tecnologia,tipo,canais", [
    ("RF", "CONTROLE_RF", 1), ("RF", "CONTROLE_RF", 6), ("WIFI_RF", "CONTROLE_RF", 16),
    ("CONTATO_SECO", "BOTAO", None), ("CONTATO_SECO", "INTERRUPTOR", None),
])
def test_acessorios_apenas_com_vinculo_aprovado_e_compatibilidade_de_tecnologia(configurada, tecnologia, tipo, canais):
    db, p, receita, _ = configurada
    motor = receita["motores"]["56mm"]
    acessorio = _insumo(db, "TEST-COMANDO-OPCIONAL", "UN", 56, 20)
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": tecnologia,
        "tubos": {"56mm": receita["tubos"]["56mm"]}, "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
        "faixas_tubo": [receita["faixas_tubo"][1]],
        "acessorios_comando": [{"insumo": acessorio, "tipo": tipo, "canais": canais}]}]
    _salvar_config(db, p, receita)
    dados = entrada(p, motor_produto_id=motor["produto_id"])
    opcoes = listar_acessorios_comando_rolo(db, [dados], 1)
    assert [(a["tipo"], a["canais"]) for a in opcoes] == [(tipo, canais)]
    with pytest.raises(ValueError, match="empresa"):
        listar_acessorios_comando_rolo(db, [dados], 2)
    db.get(ProdutoDB, acessorio["produto_id"]).situacao = "Inativo"
    db.flush()
    with pytest.raises(ValueError, match="inativo"):
        listar_acessorios_comando_rolo(db, [dados], 1)


def test_controle_nao_oferecido_quando_um_motor_nao_tem_vinculo(configurada):
    db, p, receita, _ = configurada
    primeiro = receita["motores"]["56mm"]
    segundo = _insumo(db, "TEST-SEGUNDO-MOTOR", "UN", 56, 100)
    controle = _insumo(db, "TEST-CONTROLE-COMUM", "UN", 56, 20)
    comum = {"torque_nm": 6, "tecnologia": "RF", "tubos": {"56mm": receita["tubos"]["56mm"]},
             "kits_motor": {"56mm": receita["kits_motor"]["56mm"]}, "faixas_tubo": [receita["faixas_tubo"][1]]}
    receita["conjuntos_motor"] = [
        {**comum, "motor": primeiro, "acessorios_comando": [{"insumo": controle, "tipo": "CONTROLE_RF", "canais": 1}]},
        {**comum, "motor": segundo, "acessorios_comando": []},
    ]
    _salvar_config(db, p, receita)
    assert listar_acessorios_comando_rolo(db, [entrada(p, motor_produto_id=primeiro["produto_id"]),
        entrada(p, motor_produto_id=segundo["produto_id"])], 1) == []


def test_endpoint_acessorios_multitenant_sem_gravacao(configurada):
    db, p, receita, _ = configurada
    motor = receita["motores"]["56mm"]
    controle = _insumo(db, "TEST-CONTROLE-ENDPOINT", "UN", 56, 20)
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "RF",
        "tubos": {"56mm": receita["tubos"]["56mm"]}, "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
        "faixas_tubo": [receita["faixas_tubo"][1]],
        "acessorios_comando": [{"insumo": controle, "tipo": "CONTROLE_RF", "canais": 16}]}]
    _salvar_config(db, p, receita)
    app = FastAPI()
    app.include_router(router, prefix="/orcamentos")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1, user_id=1)
    payload = [{"produto_id": p.id, "largura": 1.3, "altura": 2, "quantidade": 1,
                "cor": "AMENDOA", "acionamento": "motorizado", "motor_produto_id": motor["produto_id"],
                "kit_produto_id": receita["kits_motor"]["56mm"]["produto_id"]}]
    with TestClient(app) as client, patch.object(db, "commit", side_effect=AssertionError("Não persistir consulta")):
        resposta = client.post("/orcamentos/acessorios-comando-rolo", json=payload)
        assert resposta.status_code == 200 and resposta.json()[0]["canais"] == 16
        app.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=2, user_id=1)
        assert client.post("/orcamentos/acessorios-comando-rolo", json=payload).status_code == 422


@pytest.mark.parametrize("schema,item_model", [(OrcamentoInput, OrcamentoItemDB), (PedidoCreate, PedidoItemDB)])
def test_selecao_motor_configurado_recalculo_e_persistencia(configurada, schema, item_model):
    db, p, receita, _ = configurada
    segundo = _insumo(db, "TEST-MOTOR-WIFI", "UN", 56, 160)
    receita["conjuntos_motor"] = [
        {"motor": receita["motores"]["56mm"], "torque_nm": 6, "tecnologia": "RF",
         "tubos": {"56mm": receita["tubos"]["56mm"]},
         "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
         "faixas_tubo": [receita["faixas_tubo"][1]]},
        {"motor": segundo, "torque_nm": 10, "tecnologia": "WIFI_RF",
         "tubos": {"56mm": receita["tubos"]["56mm"]},
         "kits_motor": {"56mm": receita["kits_motor"]["56mm"]},
         "faixas_tubo": [receita["faixas_tubo"][1]]},
    ]
    _salvar_config(db, p, receita)
    opcoes = listar_motores_rolo(db, p, entrada(p), 1)
    assert [opcao["produto_id"] for opcao in opcoes] == [receita["motores"]["56mm"]["produto_id"], segundo["produto_id"]]
    with pytest.raises(ValueError, match="Selecione um motor"):
        simular_rolo_catalogo(db, p, entrada(p, motor_produto_id=None), 1)
    with pytest.raises(ValueError, match="motor não encontrado na empresa"):
        simular_rolo_catalogo(db, p, entrada(p, motor_produto_id=999999), 1)
    primeira = simular_rolo_catalogo(db, p, entrada(p, motor_produto_id=opcoes[0]["produto_id"]), 1)
    segunda = simular_rolo_catalogo(db, p, entrada(p, motor_produto_id=segundo["produto_id"]), 1)
    assert segunda["preco_unitario"] > primeira["preco_unitario"]
    assert segunda["componentes_tecnicos"]["motor"]["tecnologia"] == "WIFI_RF"
    payload = schema(cliente_id=1, itens=[{"produto_id": p.id, "descricao": p.nome, "unidade": "M2",
        "largura": 1.3, "altura": 2, "quantidade": 1, "cor": "AMENDOA", "acionamento": "motorizado",
        "preco_unitario": 0, "dados_tecnicos": {"rolo": {"motor_produto_id": segundo["produto_id"],
            "kit_produto_id": receita["kits_motor"]["56mm"]["produto_id"]}}}])
    doc = SimpleNamespace(itens=[])
    calcular_itens(db, doc, payload, 1, item_model)
    assert doc.itens[0].dados_tecnicos["rolo"]["motor_produto_id"] == segundo["produto_id"]
    assert doc.itens[0].preco_unitario == segunda["preco_unitario"]
    assert doc.itens[0].dados_tecnicos["rolo"]["motor"]["tecnologia"] == "WIFI_RF"
    with pytest.raises(ValueError, match="empresa"):
        listar_motores_rolo(db, p, entrada(p), 2)
    with pytest.raises(ValueError, match="faixa técnica"):
        simular_rolo_catalogo(db, p, entrada(p, motor_produto_id=segundo["produto_id"], altura=3.1), 1)


def test_duas_cores_no_mesmo_id_e_precedencia_da_chave_especifica(configurada):
    db, p, receita, _ = configurada
    bege = acabado(db, cor="BEGE")
    bege_manual = db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(bege.id)]
    especifica = copy.deepcopy(receita)
    especifica["cor_tecido"] = "BEGE"
    especifica["tecido"] = copy.deepcopy(bege_manual["tecido"])
    _salvar_config(db, p, especifica, f"{p.id}:motorizado:BEGE")
    for cor in ["AMENDOA", "BEGE"]:
        result = simular_rolo_catalogo(db, p, entrada(p, cor=cor), 1)
        assert result["componentes_tecnicos"]["tecido"]["cor"] == cor
    assert p.id != bege.id
    assert p.cor == "AMENDOA", "a seleção não altera a identidade do acabado no cadastro"


@pytest.mark.parametrize("ausente", ["motores", "kits_motor", "faixas_tubo"])
def test_falta_de_vinculo_bloqueia_so_acionamento_afetado(configurada, ausente):
    db, p, receita, manual = configurada
    receita[ausente] = [] if ausente == "faixas_tubo" else {}
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p), 1)
    assert simular_rolo_catalogo(db, p, entrada(p, acionamento="manual"), 1) == manual


@pytest.mark.parametrize("campo,valor", [("custo", 0), ("situacao", "Inativo"), ("empresa_id", 2)])
def test_motor_sem_custo_inativo_ou_de_outra_empresa_e_rejeitado(configurada, campo, valor):
    db, p, receita, manual = configurada
    motor = db.get(ProdutoDB, receita["motores"]["56mm"]["produto_id"])
    if campo == "custo":
        motor.custo_final = motor.valor_custo = valor
    else:
        setattr(motor, campo, valor)
    db.flush()
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p), 1)
    assert simular_rolo_catalogo(db, p, entrada(p, acionamento="manual"), 1) == manual


def test_bitola_motor_e_kit_precisam_corresponder(configurada):
    db, p, receita, _ = configurada
    receita["kits_motor"]["56mm"]["diametro_mm"] = 41
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p), 1)


def test_faixas_ambiguas_ou_medida_sem_aprovacao_nao_escolhem_motor(configurada):
    db, p, receita, _ = configurada
    receita["faixas_tubo"].append(copy.deepcopy(receita["faixas_tubo"][1]))
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p), 1)
    receita["faixas_tubo"].pop()
    _salvar_config(db, p, receita)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p, altura=3.1), 1)


def test_empresa_e_cor_continuam_isoladas(configurada):
    db, p, _, _ = configurada
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p), 2)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p, cor="INEXISTENTE"), 1)


def test_chave_de_cor_normaliza_acentos_sem_trocar_acabado(configurada):
    db, p, receita, _ = configurada
    _salvar_config(db, p, receita, f"{p.id}:motorizado:AMENDOA")
    result = simular_rolo_catalogo(db, p, entrada(p, cor="amêndoa"), 1)
    assert result["componentes_tecnicos"]["tecido"]["cor"] == "AMENDOA"


def test_manual_nao_usa_faixa_de_tubo_motorizado(configurada):
    db, p, receita_motor, _ = configurada
    manual = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes["receitas_rolo_v1"][str(p.id)])
    manual["faixas_tubo"] = [copy.deepcopy(receita_motor["faixas_tubo"][1])]
    _salvar_config(db, p, manual, f"{p.id}:manual:AMENDOA")
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, p, entrada(p, acionamento="manual"), 1)


def test_orcamento_recalcula_motor_sem_outro_produto(configurada):
    db, p, _, _ = configurada
    dados = entrada(p)
    result = simular_rolo_catalogo(db, p, dados, 1)
    doc = SimpleNamespace(itens=[])
    payload = OrcamentoInput(itens=[{"produto_id": p.id, "descricao": p.nome,
        "unidade": "M2", "largura": 1.3, "altura": 2, "quantidade": 1,
        "cor": "AMENDOA", "acionamento": "motorizado", "preco_unitario": 999999,
        "dados_tecnicos": {"rolo": {"motor_produto_id": dados.motor_produto_id,
                                    "kit_produto_id": dados.kit_produto_id}}}])
    with patch.object(db, "commit", side_effect=AssertionError("Chamador controla a transação")):
        calcular_itens(db, doc, payload, 1, OrcamentoItemDB)
    assert len(doc.itens) == 1
    assert doc.itens[0].produto_id == p.id
    assert doc.itens[0].cor == "AMENDOA"
    assert str(doc.itens[0].acionamento).lower() == "motorizado"
    assert doc.itens[0].preco_unitario == result["preco_unitario"]
    assert doc.total == Decimal(str(result["subtotal"]))
