"""Politica comercial pura: nenhuma consulta, configuracao ou integracao de rotas.

Contrato de entrada para um futuro leitor confiavel:
* IDs internos positivos; enums deste modulo; tuplas e instantes UTC explicitos.
* assinaturas_candidatas contem todos os contratos relevantes para a decisao,
  incluindo cancelamentos com possivel cobertura. Nao escolher simplesmente o
  maior ID. Historico inequivocamente encerrado fica fora desse conjunto.
* completas=True so pode ser informado apos leitura integral e consistente.
* Confirmacoes representam registros administrativos auditados, com os vinculos
  e a finalidade verificados pelo leitor. Um webhook nao cria essa evidencia.
* Limites DATE do banco ainda precisam de conversao explicita, conforme o fuso
  comercial e a semantica de fim exclusivo, antes de chamar esta politica.

As estruturas abaixo sao contratos normalizados, nao novas colunas do banco.
O avaliador nao autentica a origem dos dados: nao recebe payload de cliente/Wix.
Avulsos/cortesias complementam um modulo; nunca substituem a cobertura base.
Podem ter assinatura_id=None quando independentes; nao inventar esse vinculo.
Sem relogio implicito, tolerancia temporal, modo permissivo ou dados sensiveis
na decisao. Toda janela usa inicio <= agora < fim.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class EstadoAssinatura(str, Enum):
    TRIAL = "TRIAL"
    TRIAL_EXPIRADO = "TRIAL_EXPIRADO"
    PENDENTE = "PENDENTE"
    ATIVA = "ATIVA"
    PROXIMA_VENCIMENTO = "PROXIMA_VENCIMENTO"
    VENCIDA = "VENCIDA"
    SUSPENSA = "SUSPENSA"
    CANCELADA = "CANCELADA"


class EstadoPagamento(str, Enum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    PAGO = "PAGO"
    ATRASADO = "ATRASADO"
    ESTORNADO = "ESTORNADO"
    CANCELADO = "CANCELADO"


class TipoCobranca(str, Enum):
    ASSINATURA = "ASSINATURA"
    MODULO_AVULSO = "MODULO_AVULSO"


class OrigemConcessao(str, Enum):
    PLANO = "PLANO"
    TRIAL = "TRIAL"
    AVULSO = "AVULSO"
    CORTESIA = "CORTESIA"


class EstadoConcessao(str, Enum):
    ATIVO = "ATIVO"
    PENDENTE = "PENDENTE"
    SUSPENSO = "SUSPENSO"
    CANCELADO = "CANCELADO"
    REVOGADO = "REVOGADO"


class ModalidadeCancelamento(str, Enum):
    FIM_VIGENCIA = "FIM_VIGENCIA"
    IMEDIATO = "IMEDIATO"
    DESCONHECIDA = "DESCONHECIDA"


class MotivoAcesso(str, Enum):
    PAGO_PERMITIDO = "PAGO_PERMITIDO"
    TRIAL_PERMITIDO = "TRIAL_PERMITIDO"
    DADOS_INVALIDOS = "DADOS_INVALIDOS"
    EVIDENCIAS_INCOMPLETAS = "EVIDENCIAS_INCOMPLETAS"
    EMPRESA_DIVERGENTE = "EMPRESA_DIVERGENTE"
    VINCULO_DIVERGENTE = "VINCULO_DIVERGENTE"
    ASSINATURA_AUSENTE = "ASSINATURA_AUSENTE"
    CONTRATOS_CONFLITANTES = "CONTRATOS_CONFLITANTES"
    ASSINATURA_PENDENTE = "ASSINATURA_PENDENTE"
    ASSINATURA_SUSPENSA = "ASSINATURA_SUSPENSA"
    ASSINATURA_VENCIDA = "ASSINATURA_VENCIDA"
    ACESSO_REVOGADO = "ACESSO_REVOGADO"
    CANCELAMENTO_AMBIGUO = "CANCELAMENTO_AMBIGUO"
    COBERTURA_FUTURA = "COBERTURA_FUTURA"
    COBERTURA_ENCERRADA = "COBERTURA_ENCERRADA"
    PAGAMENTO_NAO_COMPROVADO = "PAGAMENTO_NAO_COMPROVADO"
    CONFIRMACAO_ADMINISTRATIVA_AUSENTE = "CONFIRMACAO_ADMINISTRATIVA_AUSENTE"
    CONFIRMACAO_INCONSISTENTE = "CONFIRMACAO_INCONSISTENTE"
    CICLOS_CONFLITANTES = "CICLOS_CONFLITANTES"
    TRIAL_INVALIDO = "TRIAL_INVALIDO"
    PLANO_NAO_COMPROVADO = "PLANO_NAO_COMPROVADO"
    MODULO_NAO_CONTRATADO = "MODULO_NAO_CONTRATADO"
    MODULO_BLOQUEADO = "MODULO_BLOQUEADO"
    CONCESSAO_NAO_COMPROVADA = "CONCESSAO_NAO_COMPROVADA"


@dataclass(frozen=True)
class Periodo:
    inicio: datetime
    fim: datetime


@dataclass(frozen=True)
class ConfirmacaoPagamento:
    auditoria_id: int
    empresa_id: int
    assinatura_id: int
    cobranca_id: int
    periodo: Periodo
    confirmado_em: datetime


@dataclass(frozen=True)
class ConfirmacaoConcessao:
    """Evidencia especifica de um direito avulso/cortesia, nao uma chave geral.

    Para AVULSO, o leitor deve comprovar tambem a liquidacao que fundamenta
    esse direito. Nao inferir isso de um registro ATIVO ou do webhook.
    """
    auditoria_id: int
    empresa_id: int
    assinatura_id: int | None
    concessao_id: int
    modulo_id: int
    origem: OrigemConcessao
    periodo: Periodo
    confirmado_em: datetime


@dataclass(frozen=True)
class Cancelamento:
    modalidade: ModalidadeCancelamento
    auditoria_id: int
    empresa_id: int
    assinatura_id: int
    confirmado_em: datetime
    fim_vigencia: datetime | None = None


@dataclass(frozen=True)
class Assinatura:
    id: int
    empresa_id: int
    estado: EstadoAssinatura
    plano_id: int | None
    periodo_trial: Periodo | None = None
    cancelamento: Cancelamento | None = None


@dataclass(frozen=True)
class CicloCobranca:
    id: int
    empresa_id: int
    assinatura_id: int
    tipo: TipoCobranca
    estado: EstadoPagamento
    periodo: Periodo
    pago_em: datetime | None = None
    confirmacao: ConfirmacaoPagamento | None = None


@dataclass(frozen=True)
class ConcessaoModulo:
    id: int
    empresa_id: int
    assinatura_id: int | None
    modulo_id: int
    origem: OrigemConcessao
    estado: EstadoConcessao
    periodo: Periodo
    plano_id: int | None = None
    incluido_no_plano: bool = False
    confirmacao: ConfirmacaoConcessao | None = None


@dataclass(frozen=True)
class ConsultaAcesso:
    empresa_id: int
    modulo_id: int
    agora: datetime


@dataclass(frozen=True)
class EvidenciasComerciais:
    assinaturas_candidatas: tuple[Assinatura, ...] = ()
    ciclos: tuple[CicloCobranca, ...] = ()
    concessoes: tuple[ConcessaoModulo, ...] = ()
    completas: bool = False
    conflito_impeditivo: bool = False
    modulos_bloqueados: tuple[int, ...] = ()


@dataclass(frozen=True)
class DecisaoAcesso:
    permitido: bool
    motivo: MotivoAcesso


def _id(valor):
    return type(valor) is int and valor > 0


def _instante(valor):
    # O leitor normaliza o fuso; nao comparar DATE, datetime naive ou strings.
    return type(valor) is datetime and valor.tzinfo is timezone.utc


def _periodo(valor):
    return (type(valor) is Periodo and _instante(valor.inicio)
            and _instante(valor.fim) and valor.inicio < valor.fim)


def _confirmacao_pagamento(valor):
    return (type(valor) is ConfirmacaoPagamento
            and all(_id(v) for v in (valor.auditoria_id, valor.empresa_id,
                                    valor.assinatura_id, valor.cobranca_id))
            and _periodo(valor.periodo) and _instante(valor.confirmado_em))


def _confirmacao_concessao(valor):
    return (type(valor) is ConfirmacaoConcessao
            and all(_id(v) for v in (valor.auditoria_id, valor.empresa_id,
                                    valor.concessao_id, valor.modulo_id))
            and (valor.assinatura_id is None or _id(valor.assinatura_id))
            and type(valor.origem) is OrigemConcessao
            and _periodo(valor.periodo) and _instante(valor.confirmado_em))


def _cancelamento(valor):
    return (type(valor) is Cancelamento
            and type(valor.modalidade) is ModalidadeCancelamento
            and all(_id(v) for v in (valor.auditoria_id, valor.empresa_id, valor.assinatura_id))
            and _instante(valor.confirmado_em)
            and (valor.fim_vigencia is None or _instante(valor.fim_vigencia)))


def _assinatura(valor):
    return (type(valor) is Assinatura and _id(valor.id) and _id(valor.empresa_id)
            and type(valor.estado) is EstadoAssinatura
            and (valor.plano_id is None or _id(valor.plano_id))
            and (valor.periodo_trial is None or _periodo(valor.periodo_trial))
            and (valor.cancelamento is None or _cancelamento(valor.cancelamento)))


def _ciclo(valor):
    return (type(valor) is CicloCobranca
            and all(_id(v) for v in (valor.id, valor.empresa_id, valor.assinatura_id))
            and type(valor.tipo) is TipoCobranca and type(valor.estado) is EstadoPagamento
            and _periodo(valor.periodo)
            and (valor.pago_em is None or _instante(valor.pago_em))
            and (valor.confirmacao is None or _confirmacao_pagamento(valor.confirmacao)))


def _concessao(valor):
    return (type(valor) is ConcessaoModulo
            and all(_id(v) for v in (valor.id, valor.empresa_id, valor.modulo_id))
            and (valor.assinatura_id is None or _id(valor.assinatura_id))
            and type(valor.origem) is OrigemConcessao
            and (valor.assinatura_id is not None
                 or valor.origem in (OrigemConcessao.AVULSO, OrigemConcessao.CORTESIA))
            and type(valor.estado) is EstadoConcessao and _periodo(valor.periodo)
            and (valor.plano_id is None or _id(valor.plano_id))
            and type(valor.incluido_no_plano) is bool
            and (valor.confirmacao is None or _confirmacao_concessao(valor.confirmacao)))


def _estrutura_valida(consulta, evidencias):
    return (type(consulta) is ConsultaAcesso
            and _id(consulta.empresa_id) and _id(consulta.modulo_id) and _instante(consulta.agora)
            and type(evidencias) is EvidenciasComerciais
            and type(evidencias.completas) is bool and type(evidencias.conflito_impeditivo) is bool
            and type(evidencias.assinaturas_candidatas) is tuple
            and all(_assinatura(v) for v in evidencias.assinaturas_candidatas)
            and type(evidencias.ciclos) is tuple and all(_ciclo(v) for v in evidencias.ciclos)
            and type(evidencias.concessoes) is tuple and all(_concessao(v) for v in evidencias.concessoes)
            and type(evidencias.modulos_bloqueados) is tuple
            and all(_id(v) for v in evidencias.modulos_bloqueados))


def _contem(periodo, agora):
    return periodo.inicio <= agora < periodo.fim


def _negar(motivo):
    return DecisaoAcesso(False, motivo)


def _validar_vinculos(consulta, evidencias, assinatura):
    empresa = consulta.empresa_id
    if any(v.empresa_id != empresa for v in (
        *evidencias.assinaturas_candidatas, *evidencias.ciclos, *evidencias.concessoes,
    )):
        return MotivoAcesso.EMPRESA_DIVERGENTE
    if (any(v.assinatura_id != assinatura.id for v in evidencias.ciclos)
            or any(v.assinatura_id not in (None, assinatura.id) for v in evidencias.concessoes)):
        return MotivoAcesso.VINCULO_DIVERGENTE
    for ciclo in evidencias.ciclos:
        prova = ciclo.confirmacao
        if prova is not None:
            if prova.empresa_id != empresa:
                return MotivoAcesso.EMPRESA_DIVERGENTE
            if (prova.assinatura_id != assinatura.id or prova.cobranca_id != ciclo.id
                    or prova.periodo != ciclo.periodo):
                return MotivoAcesso.VINCULO_DIVERGENTE
    for concessao in evidencias.concessoes:
        prova = concessao.confirmacao
        if prova is not None:
            if prova.empresa_id != empresa:
                return MotivoAcesso.EMPRESA_DIVERGENTE
            if (prova.assinatura_id != concessao.assinatura_id or prova.concessao_id != concessao.id
                    or prova.modulo_id != concessao.modulo_id or prova.origem is not concessao.origem
                    or prova.periodo != concessao.periodo):
                return MotivoAcesso.VINCULO_DIVERGENTE
    if len({v.id for v in evidencias.ciclos}) != len(evidencias.ciclos):
        return MotivoAcesso.CICLOS_CONFLITANTES
    provas = [v.confirmacao for v in (*evidencias.ciclos, *evidencias.concessoes)
              if v.confirmacao is not None]
    auditorias = [v.auditoria_id for v in provas]
    if assinatura.cancelamento is not None:
        auditorias.append(assinatura.cancelamento.auditoria_id)
    if len(auditorias) != len(set(auditorias)):
        return MotivoAcesso.CONFIRMACAO_INCONSISTENTE
    cancelamento = assinatura.cancelamento
    if cancelamento is not None:
        if cancelamento.empresa_id != empresa:
            return MotivoAcesso.EMPRESA_DIVERGENTE
        if cancelamento.assinatura_id != assinatura.id:
            return MotivoAcesso.VINCULO_DIVERGENTE
    return None


def _validar_ciclos(ciclos, agora):
    relevantes = [v for v in ciclos if v.estado is not EstadoPagamento.CANCELADO]
    for indice, ciclo in enumerate(relevantes):
        for outro in relevantes[indice + 1:]:
            if (ciclo.periodo.inicio < outro.periodo.fim
                    and outro.periodo.inicio < ciclo.periodo.fim):
                return MotivoAcesso.CICLOS_CONFLITANTES
    for ciclo in ciclos:
        if ciclo.tipo is not TipoCobranca.ASSINATURA:
            return MotivoAcesso.PAGAMENTO_NAO_COMPROVADO
        prova = ciclo.confirmacao
        if ciclo.estado is EstadoPagamento.PAGO:
            if ciclo.pago_em is None or ciclo.pago_em > agora:
                return MotivoAcesso.PAGAMENTO_NAO_COMPROVADO
            if prova is None:
                return MotivoAcesso.CONFIRMACAO_ADMINISTRATIVA_AUSENTE
            if prova.confirmado_em > agora or prova.confirmado_em < ciclo.pago_em:
                return MotivoAcesso.CONFIRMACAO_INCONSISTENTE
        elif ciclo.estado in (EstadoPagamento.PENDENTE, EstadoPagamento.PROCESSANDO, EstadoPagamento.ATRASADO):
            if ciclo.pago_em is not None or prova is not None:
                return MotivoAcesso.CONFIRMACAO_INCONSISTENTE
    return None


def _validar_modulo(consulta, evidencias, assinatura, trial):
    if consulta.modulo_id in evidencias.modulos_bloqueados:
        return MotivoAcesso.MODULO_BLOQUEADO
    if len({v.id for v in evidencias.concessoes}) != len(evidencias.concessoes):
        return MotivoAcesso.CONCESSAO_NAO_COMPROVADA
    candidatas = [v for v in evidencias.concessoes
                  if v.modulo_id == consulta.modulo_id
                  and v.estado is EstadoConcessao.ATIVO and _contem(v.periodo, consulta.agora)]
    for concessao in candidatas:
        if concessao.origem is OrigemConcessao.PLANO:
            if (not trial and assinatura.plano_id is not None
                    and concessao.plano_id == assinatura.plano_id and concessao.incluido_no_plano):
                return None
        elif concessao.origem is OrigemConcessao.TRIAL:
            if trial and concessao.plano_id == assinatura.plano_id:
                return None
        else:
            prova = concessao.confirmacao
            if prova is not None and prova.confirmado_em <= consulta.agora:
                return None
    if candidatas:
        return MotivoAcesso.CONCESSAO_NAO_COMPROVADA
    return MotivoAcesso.MODULO_NAO_CONTRATADO


def avaliar_acesso_comercial(
    consulta: ConsultaAcesso,
    evidencias: EvidenciasComerciais | None,
) -> DecisaoAcesso:
    """Devolve apenas permitido/motivo; nao escreve nem corrige os dados.

    Precedencia: estrutura, completude/conflitos, escopo, bloqueios do contrato,
    cancelamento, integridade dos ciclos, janela de cobertura e direito de
    modulo. Nenhum resultado autoriza uma empresa ou modulo diferente da consulta.
    """
    if not _estrutura_valida(consulta, evidencias):
        return _negar(MotivoAcesso.DADOS_INVALIDOS)
    if not evidencias.completas:
        return _negar(MotivoAcesso.EVIDENCIAS_INCOMPLETAS)
    if evidencias.conflito_impeditivo or len(evidencias.assinaturas_candidatas) > 1:
        return _negar(MotivoAcesso.CONTRATOS_CONFLITANTES)
    if not evidencias.assinaturas_candidatas:
        return _negar(MotivoAcesso.ASSINATURA_AUSENTE)
    assinatura, = evidencias.assinaturas_candidatas
    motivo = _validar_vinculos(consulta, evidencias, assinatura)
    if motivo is not None:
        return _negar(motivo)
    if assinatura.estado is EstadoAssinatura.SUSPENSA:
        return _negar(MotivoAcesso.ASSINATURA_SUSPENSA)
    if assinatura.estado is EstadoAssinatura.PENDENTE:
        return _negar(MotivoAcesso.ASSINATURA_PENDENTE)
    if assinatura.estado is EstadoAssinatura.VENCIDA:
        return _negar(MotivoAcesso.ASSINATURA_VENCIDA)
    if assinatura.estado is EstadoAssinatura.TRIAL_EXPIRADO:
        return _negar(MotivoAcesso.COBERTURA_ENCERRADA)
    cancelamento = assinatura.cancelamento
    if cancelamento is not None:
        if cancelamento.modalidade is ModalidadeCancelamento.IMEDIATO:
            return _negar(MotivoAcesso.ACESSO_REVOGADO)
        if (cancelamento.modalidade is ModalidadeCancelamento.DESCONHECIDA
                or cancelamento.confirmado_em > consulta.agora
                or cancelamento.fim_vigencia is None
                or cancelamento.fim_vigencia <= cancelamento.confirmado_em):
            return _negar(MotivoAcesso.CANCELAMENTO_AMBIGUO)
        # FIM_VIGENCIA nao pode encurtar silenciosamente cobertura ja paga.
        if any(v.estado is EstadoPagamento.PAGO and v.periodo.fim > cancelamento.fim_vigencia
               for v in evidencias.ciclos):
            return _negar(MotivoAcesso.CANCELAMENTO_AMBIGUO)
        if consulta.agora >= cancelamento.fim_vigencia:
            return _negar(MotivoAcesso.COBERTURA_ENCERRADA)
    elif assinatura.estado is EstadoAssinatura.CANCELADA:
        return _negar(MotivoAcesso.CANCELAMENTO_AMBIGUO)
    motivo = _validar_ciclos(evidencias.ciclos, consulta.agora)
    if motivo is not None:
        return _negar(motivo)
    trial = assinatura.estado is EstadoAssinatura.TRIAL
    if trial:
        periodo = assinatura.periodo_trial
        if periodo is None:
            return _negar(MotivoAcesso.TRIAL_INVALIDO)
        if consulta.agora < periodo.inicio:
            return _negar(MotivoAcesso.COBERTURA_FUTURA)
        if consulta.agora >= periodo.fim:
            return _negar(MotivoAcesso.COBERTURA_ENCERRADA)
    else:
        if assinatura.plano_id is None:
            return _negar(MotivoAcesso.PLANO_NAO_COMPROVADO)
        pagos = [v for v in evidencias.ciclos if v.estado is EstadoPagamento.PAGO]
        if not any(_contem(v.periodo, consulta.agora) for v in pagos):
            if any(v.periodo.inicio > consulta.agora for v in pagos):
                return _negar(MotivoAcesso.COBERTURA_FUTURA)
            if pagos:
                return _negar(MotivoAcesso.COBERTURA_ENCERRADA)
            return _negar(MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)
    motivo = _validar_modulo(consulta, evidencias, assinatura, trial)
    if motivo is not None:
        return _negar(motivo)
    return DecisaoAcesso(True, MotivoAcesso.TRIAL_PERMITIDO if trial else MotivoAcesso.PAGO_PERMITIDO)

