"""Vínculos sintéticos isolados: nenhuma combinação real é homologada aqui."""
import copy

import pytest

from app.models.empresa import EmpresaDB
from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.orcamento import OrcamentoItemDB
from app.schemas.orcamento import OrcamentoInput
from app.schemas.rolo_receita import ConjuntoMotorRolo
from app.services.composicao_comercial import calcular_itens
from app.services.rolo_receita import (
    _bitolas_motor_compativeis,
    _perfil_motor_rolo,
    listar_acessorios_comando_rolo,
    listar_motores_rolo,
    simular_rolo_catalogo,
)
from app.services.rolo_simulacao import RoloSimulacaoInput
from test_rolo_picasso import (
    _componente_tecnico,
    _equivalencia_tecnica,
    _preparar_motores_dinamicos,
    ativar,
    acabado,
    configurar_screen_importado,
    picasso,  # noqa: F401
)
from types import SimpleNamespace


def _configurar(picasso, torque, diametro):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    motor = _componente_tecnico(db, "Motor sintético", "UN", 100)
    tubo = _componente_tecnico(db, "Tubo sintético", "ML", 20)
    kit = _componente_tecnico(db, "Kit sintético", "KIT", 30)
    comum = {
        "fabricante": "TESTE", "perfil_tubo": "PERFIL TESTE",
        "diametro_mm": diametro, "familia_instalacao": "FAMILIA TESTE",
        "motores_compativeis": [motor.id],
    }
    vinculo_motor = _equivalencia_tecnica(db, motor, "MOTOR_PERSIANA", {
        "fabricante": "TESTE", "familia": "ROLO", "torque_nm": torque,
        "tecnologia": "RF", "perfil_rolo": {
            "perfil_tubo": "PERFIL TESTE", "diametro_mm": diametro,
            "familia_instalacao": "FAMILIA TESTE", "largura_max_m": 3,
            "altura_max_m": 3, "capacidade_kg": 10, "peso_barra_kg": 1,
            "peso_estimado_kg_m2": 0.5, "codigos_kit": ["KIT TESTE"],
            "origem": "Somente teste sintético",
        },
    })
    _equivalencia_tecnica(db, tubo, f"TUBO_ROLO_{diametro}MM", comum)
    vinculo_kit = _equivalencia_tecnica(db, kit, "KIT_INSTALACAO_MOTOR_ROLO", {
        **comum, "papel": "KIT_INSTALACAO", "codigo_kit": "KIT TESTE",
    })
    for papel in ("SUPORTE", "ADAPTADOR", "PONTEIRA"):
        acessorio = _componente_tecnico(db, papel, "UN", 5)
        _equivalencia_tecnica(db, acessorio, "ACESSORIO_MOTOR", {
            **comum, "papel": papel, "tecnologias_compativeis": ["RF"],
            "quantidade_por_persiana": 1,
        })
    empresa = db.get(EmpresaDB, 1)
    config = copy.deepcopy(empresa.configuracoes)
    receita = copy.deepcopy(config["receitas_rolo_v1"][str(produto.id)])
    receita["tubos"] = {f"{diametro}mm": {
        "produto_id": tubo.id, "codigo_interno": tubo.codigo_interno,
        "unidade_tecnica": "ML", "preco_compra": 20, "ipi_percentual": None,
        "unidades_por_compra": 1, "origem": "Somente teste sintético",
        "diametro_mm": diametro,
    }}
    receita["faixas_tubo"] = [{
        "diametro_mm": diametro, "largura_min_m": 0, "largura_max_m": 3,
        "altura_max_m": 3, "origem": "Somente teste sintético",
    }]
    config["receitas_rolo_v1"][f"{produto.id}:motorizado"] = receita
    empresa.configuracoes = config
    db.flush()
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1,
        cor="AMENDOA", acionamento="motorizado",
    )
    return db, produto, motor, tubo, vinculo_motor, vinculo_kit, entrada


@pytest.mark.parametrize("torque,diametro", [
    (0.5, 38), (6, 32), (6, 38), (6, 43), (10, 41), (10, 53), (13, 38), (13, 70),
])
def test_motor_exige_tubo_da_receita_e_kit_explicito(picasso, torque, diametro):
    db, produto, motor, tubo, _, kit, entrada = _configurar(picasso, torque, diametro)
    opcoes = listar_motores_rolo(db, produto, entrada, 1)
    assert [(item["produto_id"], item["diametro_tubo_mm"]) for item in opcoes] == [
        (motor.id, diametro),
    ]
    resultado = simular_rolo_catalogo(
        db, produto, entrada.model_copy(update={"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id}), 1,
    )
    assert resultado["componentes_tecnicos"]["tubo"]["produto_codigo"] == tubo.codigo_interno
    assert resultado["bitola_tecnica"] == f"{diametro}mm"
    categorias = [item["categoria"] for item in resultado["fabricacao_por_peca"]["componentes"]]
    assert categorias.count("Motor") == categorias.count("Acessórios do motor") == 1


@pytest.mark.parametrize("torque,diametro", [(0.5, 32), (0.5, 41), (0.8, 38), (1.2, 38)])
def test_torque_incompativel_nao_aparece_nem_simula(picasso, torque, diametro):
    db, produto, motor, _, _, kit, entrada = _configurar(picasso, torque, diametro)
    with pytest.raises(ValueError, match="Nenhum conjunto"):
        listar_motores_rolo(db, produto, entrada, 1)
    with pytest.raises(ValueError, match="sem composição dinâmica aprovada"):
        simular_rolo_catalogo(db, produto, entrada.model_copy(update={"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id}), 1)


@pytest.mark.parametrize("pendencia", ["kit", "carga", "outro_tubo"])
def test_ausencia_de_comprovacao_bloqueia_seletor_e_simulacao(picasso, pendencia):
    db, produto, motor, tubo, vinculo_motor, kit, entrada = _configurar(picasso, 13, 38)
    if pendencia == "kit":
        kit.ativo = False
    elif pendencia == "carga":
        config = copy.deepcopy(vinculo_motor.configuracoes_locais)
        config["perfil_rolo"]["capacidade_kg"] = 1
        vinculo_motor.configuracoes_locais = config
    else:
        vinculo = db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
            funcao_tecnica="TUBO_ROLO_38MM", produto_id=tubo.id,
        ).one()
        outro = _componente_tecnico(db, "Outro tubo sintético", "ML", 20)
        vinculo.produto_id = outro.id
    db.flush()
    with pytest.raises(ValueError, match="Nenhum conjunto"):
        listar_motores_rolo(db, produto, entrada, 1)
    with pytest.raises(ValueError, match="sem composição dinâmica aprovada"):
        simular_rolo_catalogo(db, produto, entrada.model_copy(update={"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id}), 1)


def test_salvar_revalida_motor_e_kit(picasso):
    db, produto, motor, _, _, kit, entrada = _configurar(picasso, 13, 38)
    payload = OrcamentoInput(cliente_id=1, itens=[{
        "produto_id": produto.id, "descricao": produto.nome, "unidade": "M2",
        "largura": entrada.largura, "altura": entrada.altura, "quantidade": 1,
        "cor": entrada.cor, "acionamento": "motorizado", "preco_unitario": 0,
        "dados_tecnicos": {"rolo": {"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id}},
    }])
    documento = SimpleNamespace(itens=[])
    calcular_itens(db, documento, payload, 1, OrcamentoItemDB)
    assert documento.itens[0].dados_tecnicos["rolo"]["motor_produto_id"] == motor.id
    assert documento.itens[0].dados_tecnicos["rolo"]["kit_produto_id"] == kit.produto_id
    kit.ativo = False
    db.flush()
    with pytest.raises(ValueError, match="sem composição dinâmica aprovada"):
        calcular_itens(db, SimpleNamespace(itens=[]), payload, 1, OrcamentoItemDB)
    historico = documento.itens[0]
    historico.id = 123
    historico.dados_tecnicos = {"rolo": {"motor_produto_id": motor.id}}
    item_antigo = payload.itens[0].model_copy(update={
        "id": historico.id, "preco_unitario": historico.preco_unitario,
        "desconto": historico.desconto, "dados_tecnicos": historico.dados_tecnicos,
    })
    documento_historico = SimpleNamespace(itens=[historico])
    calcular_itens(db, documento_historico, payload.model_copy(update={"itens": [item_antigo]}), 1, OrcamentoItemDB)
    assert documento_historico.itens[0] is historico
    assert documento_historico.itens[0].dados_tecnicos == {"rolo": {"motor_produto_id": motor.id}}


def test_selecao_explicita_e_troca_de_kit_sintetico(picasso):
    db, produto, motor, _, _, primeiro, entrada = _configurar(picasso, 6, 38)
    segundo_produto = _componente_tecnico(db, "Segundo kit sintético", "KIT", 55)
    segundo = _equivalencia_tecnica(
        db, segundo_produto, "KIT_INSTALACAO_MOTOR_ROLO",
        copy.deepcopy(primeiro.configuracoes_locais),
    )
    escolha = entrada.model_copy(update={"motor_produto_id": motor.id})
    with pytest.raises(ValueError, match="Mais de um conjunto tecnico compativel"):
        simular_rolo_catalogo(db, produto, escolha, 1)
    opcoes = listar_motores_rolo(db, produto, entrada, 1)[0]["kits"]
    assert {k["produto_id"] for k in opcoes} == {primeiro.produto_id, segundo.produto_id}
    resultado1 = simular_rolo_catalogo(
        db, produto, escolha.model_copy(update={"kit_produto_id": primeiro.produto_id}), 1,
    )
    resultado2 = simular_rolo_catalogo(
        db, produto, escolha.model_copy(update={"kit_produto_id": segundo.produto_id}), 1,
    )
    assert resultado2["custo_tecnico"] - resultado1["custo_tecnico"] == pytest.approx(25)
    assert resultado2["preco_unitario"] > resultado1["preco_unitario"]
    assert resultado2["componentes_tecnicos"]["acessorios"][0]["produto_id"] == segundo.produto_id
    with pytest.raises(ValueError, match="kit.*incompatível"):
        simular_rolo_catalogo(db, produto, escolha.model_copy(update={"kit_produto_id": 999999}), 1)
    segundo.ativo = False
    db.flush()
    automatico = simular_rolo_catalogo(
        db, produto, escolha, 1
    )
    assert automatico["custo_tecnico"] == pytest.approx(
        resultado1["custo_tecnico"]
    )
    assert automatico["componentes_tecnicos"]["acessorios"][0][
        "produto_id"
    ] == primeiro.produto_id
    with pytest.raises(ValueError, match="kit.*incompatível"):
        simular_rolo_catalogo(db, produto, escolha.model_copy(update={"kit_produto_id": segundo.produto_id}), 1)
    segundo.ativo = True
    segundo_produto.custo_final = segundo_produto.valor_custo = 0
    db.flush()
    with pytest.raises(ValueError, match="kit.*incompatível"):
        simular_rolo_catalogo(db, produto, escolha.model_copy(update={"kit_produto_id": segundo.produto_id}), 1)
    segundo_produto.custo_final = 55
    segundo_produto.empresa_id = 2
    db.flush()
    with pytest.raises(ValueError, match="kit.*incompatível"):
        simular_rolo_catalogo(db, produto, escolha.model_copy(update={"kit_produto_id": segundo.produto_id}), 1)


def test_catalogo_sem_vinculo_informa_capacidade_compatibilidade_e_unidade(picasso):
    db, produto, motor, _, vinculo_motor, kit, entrada = _configurar(picasso, 6, 38)
    vinculo_motor.ativo = False
    produto_kit = db.get(type(motor), kit.produto_id)
    produto_kit.unidade_venda = "UN"
    db.flush()
    with pytest.raises(ValueError) as erro:
        simular_rolo_catalogo(db, produto, entrada.model_copy(update={
            "motor_produto_id": motor.id, "kit_produto_id": kit.produto_id,
        }), 1)
    mensagem = str(erro.value)
    assert "torque, capacidade e carga do motor" in mensagem
    assert "compatibilidade do kit" in mensagem
    assert "kit precisa de unidade KIT" in mensagem


def test_controle_e_componentes_no_kit_nao_sao_cobrados_em_duplicidade(picasso):
    db, produto, motor, _, _, kit, entrada = _configurar(picasso, 6, 38)
    controles = _componente_tecnico(db, "Controle sintético", "UN", 40)
    _equivalencia_tecnica(db, controles, "ACESSORIO_MOTOR", {
        "fabricante": "TESTE", "papel": "CONTROLE", "tipo": "CONTROLE_RF",
        "canais": 1, "motores_compativeis": [motor.id],
    })
    acessorios = db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
        empresa_id=1, funcao_tecnica="ACESSORIO_MOTOR",
    ).all()
    incluidos = []
    for acessorio in acessorios:
        papel = acessorio.configuracoes_locais.get("papel")
        if papel in {"SUPORTE", "ADAPTADOR", "PONTEIRA"}:
            incluidos.append({
                "papel": papel, "produto_id": acessorio.produto_id,
                "quantidade_por_persiana": 1,
            })
            acessorio.ativo = False
    kit.configuracoes_locais = {**kit.configuracoes_locais, "componentes_incluidos": incluidos}
    db.flush()
    selecionada = entrada.model_copy(update={"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id})
    assert listar_acessorios_comando_rolo(db, [selecionada], 1)[0]["produto_id"] == controles.id
    resultado = simular_rolo_catalogo(db, produto, selecionada, 1)
    componentes = resultado["fabricacao_por_peca"]["componentes"]
    categorias = [item["categoria"] for item in componentes]
    assert categorias.count("Acessórios do motor") == 1
    assert not {"Suporte do motor", "Adaptador do motor", "Ponteira do tubo"} & set(categorias)
    assert resultado["custo_tecnico"] == pytest.approx(sum(item["custo_total"] for item in componentes))


def test_tubo_de_outro_fabricante_exige_vinculo_explicito(picasso):
    db, produto, motor, tubo, vinculo_motor, _, entrada = _configurar(picasso, 13, 38)
    vinculo_motor.configuracoes_locais = {**vinculo_motor.configuracoes_locais, "fabricante": "EMTECO"}
    for vinculo in db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.funcao_tecnica.in_(
            ("KIT_INSTALACAO_MOTOR_ROLO", "ACESSORIO_MOTOR"),
        ),
    ):
        vinculo.configuracoes_locais = {**vinculo.configuracoes_locais, "fabricante": "EMTECO"}
    db.flush()
    assert listar_motores_rolo(db, produto, entrada, 1)[0]["produto_id"] == motor.id
    tubo_vinculo = db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
        funcao_tecnica="TUBO_ROLO_38MM", produto_id=tubo.id,
    ).one()
    tubo_vinculo.configuracoes_locais = {**tubo_vinculo.configuracoes_locais, "motores_compativeis": []}
    db.flush()
    with pytest.raises(ValueError, match="Nenhum conjunto"):
        listar_motores_rolo(db, produto, entrada, 1)


def test_legado_sem_torque_e_bloqueado(picasso):
    db, produto, _, _, _, _, entrada = _configurar(picasso, 6, 38)
    with pytest.raises(ValueError, match="torque"):
        simular_rolo_catalogo(db, produto, entrada, 1)


def test_screen_84_manual_preservada_e_motor_sem_kit_38_bloqueado(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = configurar_screen_importado(db)
    _, motor = _preparar_motores_dinamicos(db)
    manual = RoloSimulacaoInput(
        produto_id=84, largura=1.9, altura=2, quantidade=1,
        cor="BRANCO", acionamento="manual",
    )
    assert simular_rolo_catalogo(db, produto, manual, 1)["bitola_tecnica"] == "38mm"
    kit = db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
        empresa_id=1, funcao_tecnica="KIT_INSTALACAO_MOTOR_ROLO", ativo=True,
    ).first()
    motorizada = manual.model_copy(update={"acionamento": "motorizado", "motor_produto_id": motor.id,
                                         "kit_produto_id": kit.produto_id})
    with pytest.raises(ValueError, match="38 mm"):
        simular_rolo_catalogo(db, produto, motorizada, 1)
    assert simular_rolo_catalogo(db, produto, manual, 1)["bitola_tecnica"] == "38mm"


@pytest.mark.parametrize("torque,permitido", [(0.5, True), (0.8, False), (1.2, False), (13, True)])
def test_conjunto_explicito_seletor_e_simulacao(picasso, torque, permitido):
    db, produto, motor, tubo, vinculo_motor, kit, entrada = _configurar(picasso, torque, 38)
    empresa = db.get(EmpresaDB, 1)
    config = copy.deepcopy(empresa.configuracoes)
    receita = config["receitas_rolo_v1"][f"{produto.id}:motorizado"]

    def insumo(produto_db, unidade):
        return {
            "produto_id": produto_db.id, "codigo_interno": produto_db.codigo_interno,
            "unidade_tecnica": unidade, "preco_compra": 10, "ipi_percentual": None,
            "unidades_por_compra": 1, "origem": "Somente teste",
        }

    receita["conjuntos_motor"] = [{
        "motor": insumo(motor, "UN"), "torque_nm": torque, "tecnologia": "RF",
        "tubos": {"38mm": receita["tubos"]["38mm"]},
        "kits_motor": {"38mm": insumo(db.get(type(tubo), kit.produto_id), "KIT")},
        "faixas_tubo": receita["faixas_tubo"],
        "capacidade_kg": 10, "peso_barra_kg": 1,
        "peso_estimado_kg_m2": 0.5, "origem_carga": "Somente teste",
    }]
    empresa.configuracoes = config
    vinculo_motor.ativo = False
    db.flush()
    selecionada = entrada.model_copy(update={"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id})
    if permitido:
        assert [item["produto_id"] for item in listar_motores_rolo(db, produto, entrada, 1)] == [motor.id]
        assert simular_rolo_catalogo(db, produto, selecionada, 1)["bitola_tecnica"] == "38mm"
    else:
        with pytest.raises(ValueError):
            listar_motores_rolo(db, produto, entrada, 1)
        with pytest.raises(ValueError, match="Motor sem tubo"):
            simular_rolo_catalogo(db, produto, selecionada, 1)


@pytest.mark.parametrize("componente", ["motor", "tubo", "kit"])
def test_seletor_nao_oferece_conjunto_com_componente_inativo(picasso, componente):
    db, produto, motor, tubo, vinculo_motor, kit, entrada = _configurar(picasso, 6, 38)
    empresa = db.get(EmpresaDB, 1)
    configuracoes = copy.deepcopy(empresa.configuracoes)
    receita = configuracoes["receitas_rolo_v1"][f"{produto.id}:motorizado"]

    def insumo(produto_db, unidade):
        return {
            "produto_id": produto_db.id, "codigo_interno": produto_db.codigo_interno,
            "unidade_tecnica": unidade, "preco_compra": 10, "ipi_percentual": None,
            "unidades_por_compra": 1, "origem": "Somente teste",
        }

    kit_produto = db.get(type(tubo), kit.produto_id)
    receita["conjuntos_motor"] = [{
        "motor": insumo(motor, "UN"), "torque_nm": 6, "tecnologia": "RF",
        "tubos": {"38mm": receita["tubos"]["38mm"]},
        "kits_motor": {"38mm": insumo(kit_produto, "KIT")},
        "faixas_tubo": receita["faixas_tubo"], "capacidade_kg": 10,
        "peso_barra_kg": 1, "peso_estimado_kg_m2": 0.5,
        "origem_carga": "Somente teste",
    }]
    empresa.configuracoes = configuracoes
    vinculo_motor.ativo = False
    {"motor": motor, "tubo": tubo, "kit": kit_produto}[componente].situacao = "Inativo"
    db.flush()
    with pytest.raises(ValueError):
        listar_motores_rolo(db, produto, entrada, 1)
    with pytest.raises(ValueError):
        simular_rolo_catalogo(db, produto, entrada.model_copy(update={"motor_produto_id": motor.id, "kit_produto_id": kit.produto_id}), 1)


@pytest.mark.parametrize("torque,diametro,esperado", [
    (0.5, 38, True), (0.5, 41, False), (0.8, 38, False),
    (1.2, 38, False), (6, 38, True), (13, 41, True),
])
def test_conjunto_explicito_exige_carga_e_torque_compativeis(torque, diametro, esperado):
    def insumo(unidade):
        return {
            "produto_id": 1, "codigo_interno": "TESTE", "unidade_tecnica": unidade,
            "preco_compra": 1, "ipi_percentual": None, "unidades_por_compra": 1,
            "origem": "Somente teste", "diametro_mm": diametro,
        }

    conjunto = ConjuntoMotorRolo.model_validate({
        "motor": insumo("UN"), "torque_nm": torque, "tecnologia": "RF",
        "tubos": {f"{diametro}mm": insumo("ML")},
        "kits_motor": {f"{diametro}mm": insumo("KIT")},
        "faixas_tubo": [{
            "diametro_mm": diametro, "largura_min_m": 0, "largura_max_m": 2,
            "altura_max_m": 3, "origem": "Somente teste",
        }],
        "capacidade_kg": 10, "peso_barra_kg": 1,
        "peso_estimado_kg_m2": 0.5, "origem_carga": "Somente teste",
    })
    entrada = SimpleNamespace(largura=1.5, altura=2)
    assert bool(_bitolas_motor_compativeis(conjunto, entrada)) is esperado
    assert not _bitolas_motor_compativeis(conjunto.model_copy(update={"origem_carga": None}), entrada)
    assert not _bitolas_motor_compativeis(conjunto.model_copy(update={"capacidade_kg": 1}), entrada)


def test_emteco_seleciona_perfil_pela_bitola_sem_fixar_motor_6():
    config = {
        "fabricante": "EMTECO", "torque_nm": 6, "tipo_motor": "PLUG",
        "familia_instalacao": "628/1014NM", "tecnologia": "RF",
    }
    assert _perfil_motor_rolo(config, 1.5, 2, 43)["diametro"] == 43
    assert _perfil_motor_rolo(config, 1.5, 2, 53)["diametro"] == 53
    assert _perfil_motor_rolo(config, 1.5, 2, 38) is None


@pytest.mark.parametrize("torque", [0.5, 0.8, 1.2, 6, 10, 13, 20])
def test_schema_le_torques_inclusive_historicos(torque):
    insumo = {
        "produto_id": 1, "codigo_interno": "TESTE", "unidade_tecnica": "UN",
        "preco_compra": 1, "ipi_percentual": None, "unidades_por_compra": 1,
        "origem": "Somente teste",
    }
    conjunto = ConjuntoMotorRolo.model_validate({
        "motor": insumo, "torque_nm": torque, "tecnologia": "RF",
        "tubos": {}, "kits_motor": {}, "faixas_tubo": [{
            "diametro_mm": 38, "largura_min_m": 0, "largura_max_m": 2,
            "altura_max_m": 2, "origem": "Somente teste",
        }],
    })
    assert conjunto.torque_nm == torque
