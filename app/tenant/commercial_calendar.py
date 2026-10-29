"""Calendario comercial das assinaturas (funcoes puras, sem I/O).

Datas comerciais usam America/Sao_Paulo por padrao, ou o fuso informado
explicitamente (nome IANA ou tzinfo); instantes tecnicos sao UTC.
Periodos seguem ``inicio <= agora < fim`` (fim exclusivo).

* Nunca depende do fuso do sistema operacional nem do relogio local.
* Timestamps sem fuso exigem origem explicita; nao ha padrao implicito para
  dados historicos (nem UTC, nem Sao Paulo).
* ``estrito=True`` rejeita horario local inexistente ou ambiguo em vez de
  escolher ``fold`` em silencio. O modo padrao preserva o comportamento 4C.7.
* Datas civis (``date``) nao se confundem com timestamps: o primeiro
  instante do dia comercial nunca interpreta um timestamp historico.
* Os offsets vem do banco de fusos (inclui o horario de verao historico).
"""

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from .commercial_policy import Periodo

FUSO_COMERCIAL = ZoneInfo("America/Sao_Paulo")


def _fuso(valor: "str | tzinfo | None", padrao: "tzinfo | None" = None) -> tzinfo:
    if valor is None:
        if padrao is None:
            raise ValueError("fuso deve ser informado explicitamente")
        return padrao
    if isinstance(valor, str):
        try:
            return ZoneInfo(valor)
        except Exception as erro:  # chave invalida ou ausente no banco de fusos
            raise ValueError(f"fuso IANA invalido: {valor!r}") from erro
    if isinstance(valor, tzinfo):
        return valor
    raise TypeError("fuso deve ser str IANA ou tzinfo")


def _eh_data(valor: object) -> bool:
    # datetime herda de date; aqui so interessa o dia civil.
    return isinstance(valor, date) and not isinstance(valor, datetime)


def _exigir_data(valor: object, nome: str) -> date:
    if not _eh_data(valor):
        raise TypeError(f"{nome} deve ser date (nao datetime)")
    return valor  # type: ignore[return-value]


def _localizar_estrito(valor: datetime, zona: tzinfo) -> datetime:
    """Interpreta hora local; falha se inexistente ou ambigua."""
    candidatos = set()
    for fold in (0, 1):
        utc = valor.replace(tzinfo=zona, fold=fold).astimezone(timezone.utc)
        if utc.astimezone(zona).replace(tzinfo=None) == valor:
            candidatos.add(utc)
    if len(candidatos) == 0:
        raise ValueError("horario local inexistente no fuso informado")
    if len(candidatos) > 1:
        raise ValueError("horario local ambiguo no fuso informado")
    return candidatos.pop()


def instante_utc(
    valor: datetime,
    origem_sem_fuso: "str | tzinfo | None" = None,
    *,
    estrito: bool = False,
) -> datetime:
    """Normaliza para UTC.

    Valor com fuso preserva o instante. Valor sem fuso exige
    ``origem_sem_fuso``; com ``estrito=True`` horas inexistentes ou ambiguas
    sao rejeitadas (sem ``fold`` silencioso).
    """
    if not isinstance(valor, datetime):
        raise TypeError("valor deve ser datetime")
    if valor.tzinfo is None or valor.utcoffset() is None:
        if origem_sem_fuso is None:
            raise ValueError("timestamp sem fuso exige origem_sem_fuso explicita")
        zona = _fuso(origem_sem_fuso)
        naive = valor.replace(tzinfo=None)
        if estrito:
            return _localizar_estrito(naive, zona)
        return naive.replace(tzinfo=zona).astimezone(timezone.utc)
    return valor.astimezone(timezone.utc)


def data_comercial(
    instante: datetime,
    origem_sem_fuso: "str | tzinfo | None" = None,
    *,
    fuso: "str | tzinfo | None" = None,
    estrito: bool = False,
) -> date:
    """Dia civil do instante no fuso comercial (padrao America/Sao_Paulo)."""
    zona = _fuso(fuso, FUSO_COMERCIAL)
    return instante_utc(instante, origem_sem_fuso, estrito=estrito).astimezone(zona).date()


def inicio_dia_comercial_utc(
    dia: date, *, fuso: "str | tzinfo | None" = None, estrito: bool = False
) -> datetime:
    """Primeiro instante valido (UTC) do dia civil no fuso comercial.

    Se 00:00 nao existe (transicao de horario de verao), o dia comeca na
    transicao. Se 00:00 se repete, vale a primeira ocorrencia. Uso exclusivo
    para datas civis, nunca para interpretar timestamps historicos.
    Com ``estrito=True`` a meia-noite local inexistente ou ambigua e rejeitada.
    """
    dia = _exigir_data(dia, "dia")
    zona = _fuso(fuso, FUSO_COMERCIAL)
    local = datetime(dia.year, dia.month, dia.day)
    if estrito:
        return _localizar_estrito(local, zona)
    candidatos = []
    for fold in (0, 1):
        utc = local.replace(tzinfo=zona, fold=fold).astimezone(timezone.utc)
        if utc.astimezone(zona).date() == dia:
            candidatos.append(utc)
    if not candidatos:
        raise ValueError("nao foi possivel determinar o inicio do dia comercial")
    inicio = min(candidatos)
    # Garante que o instante imediatamente anterior pertence ao dia anterior.
    if (inicio - timedelta(microseconds=1)).astimezone(zona).date() == dia:
        raise ValueError("inicio do dia comercial inconsistente no fuso informado")
    return inicio


def fim_exclusivo_utc(
    fim: date, *, fuso: "str | tzinfo | None" = None, estrito: bool = False
) -> datetime:
    """Limite exclusivo (UTC): inicio do dia comercial de ``fim``."""
    return inicio_dia_comercial_utc(_exigir_data(fim, "fim"), fuso=fuso, estrito=estrito)


def periodo_comercial(
    inicio: date, fim: date, *, fuso: "str | tzinfo | None" = None, estrito: bool = False
) -> Periodo:
    """Periodo ``[inicio 00:00, fim 00:00)`` comercial, em UTC."""
    inicio = _exigir_data(inicio, "inicio")
    fim = _exigir_data(fim, "fim")
    if inicio >= fim:
        raise ValueError("periodo invalido: inicio deve ser anterior ao fim")
    return Periodo(
        inicio_dia_comercial_utc(inicio, fuso=fuso, estrito=estrito),
        fim_exclusivo_utc(fim, fuso=fuso, estrito=estrito),
    )


def instante_no_periodo(
    instante: datetime,
    inicio: date,
    fim: date,
    origem_sem_fuso: "str | tzinfo | None" = None,
    *,
    fuso: "str | tzinfo | None" = None,
    estrito: bool = False,
) -> bool:
    """``inicio <= instante < fim`` no calendario comercial."""
    periodo = periodo_comercial(inicio, fim, fuso=fuso, estrito=estrito)
    agora = instante_utc(instante, origem_sem_fuso, estrito=estrito)
    return periodo.inicio <= agora < periodo.fim

def proxima_data_ciclo(inicio: date, periodicidade: str) -> date:
    """Avanco de calendario (mesma matematica de ``_next_due_date`` do admin)."""
    inicio = _exigir_data(inicio, "inicio")
    tipo = str(periodicidade).upper()
    if tipo == "ANUAL":
        try:
            return inicio.replace(year=inicio.year + 1)
        except ValueError:
            return inicio.replace(year=inicio.year + 1, day=28)
    if tipo == "MENSAL":
        ano, mes = (inicio.year + 1, 1) if inicio.month == 12 else (inicio.year, inicio.month + 1)
        return date(ano, mes, min(inicio.day, monthrange(ano, mes)[1]))
    raise ValueError("periodicidade invalida")
