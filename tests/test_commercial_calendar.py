import os
import subprocess
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.tenant import commercial_calendar as cal
from app.tenant import commercial_policy as pol

UTC = timezone.utc
SP = ZoneInfo("America/Sao_Paulo")
RAIZ = Path(__file__).resolve().parents[1]


def utc(*args):
    return datetime(*args, tzinfo=UTC)


class DataComercialTest(unittest.TestCase):
    def test_utc_para_data_brasileira(self):
        self.assertEqual(cal.data_comercial(utc(2024, 5, 10, 15)), date(2024, 5, 10))

    def test_virada_de_dia_utc_x_sao_paulo(self):
        self.assertEqual(cal.data_comercial(utc(2024, 5, 11, 2, 59, 59)), date(2024, 5, 10))
        self.assertEqual(cal.data_comercial(utc(2024, 5, 11, 3, 0, 0)), date(2024, 5, 11))

    def test_aceita_instante_com_outro_fuso(self):
        tokyo = datetime(2024, 5, 11, 11, 59, tzinfo=ZoneInfo("Asia/Tokyo"))
        self.assertEqual(cal.data_comercial(tokyo), date(2024, 5, 10))

    def test_rejeita_timestamp_sem_fuso(self):
        with self.assertRaises(ValueError):
            cal.data_comercial(datetime(2024, 5, 10, 12))
        with self.assertRaises(ValueError):
            cal.instante_utc(datetime(2024, 5, 10, 12))
        with self.assertRaises(ValueError):
            cal.instante_no_periodo(datetime(2024, 5, 10, 12), date(2024, 5, 1), date(2024, 6, 1))

    def test_origem_explicita_para_timestamp_sem_fuso(self):
        naive = datetime(2024, 5, 10, 23, 30)
        self.assertEqual(cal.instante_utc(naive, UTC), utc(2024, 5, 10, 23, 30))
        self.assertEqual(cal.instante_utc(naive, SP), utc(2024, 5, 11, 2, 30))
        self.assertEqual(cal.data_comercial(naive, UTC), date(2024, 5, 10))
        self.assertEqual(cal.data_comercial(naive, SP), date(2024, 5, 10))
        self.assertEqual(cal.data_comercial(datetime(2024, 5, 10, 22), UTC), date(2024, 5, 10))

    def test_tipos_invalidos(self):
        with self.assertRaises(TypeError):
            cal.instante_utc("2024-05-10")
        with self.assertRaises(TypeError):
            cal.inicio_dia_comercial_utc(datetime(2024, 5, 10))
        with self.assertRaises(TypeError):
            cal.periodo_comercial("2024-05-01", date(2024, 6, 1))


class LimitesTest(unittest.TestCase):
    def test_inicio_do_dia_em_utc(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2024, 5, 10)), utc(2024, 5, 10, 3))
        self.assertIs(cal.inicio_dia_comercial_utc(date(2024, 5, 10)).tzinfo, UTC)

    def test_inicio_inclusivo_e_fim_exclusivo(self):
        i, f = date(2024, 5, 10), date(2024, 6, 10)
        ini, fim = utc(2024, 5, 10, 3), utc(2024, 6, 10, 3)
        self.assertTrue(cal.instante_no_periodo(ini, i, f))
        self.assertFalse(cal.instante_no_periodo(ini - timedelta(microseconds=1), i, f))
        self.assertTrue(cal.instante_no_periodo(fim - timedelta(microseconds=1), i, f))
        self.assertFalse(cal.instante_no_periodo(fim, i, f))

    def test_antes_e_depois_da_meia_noite_comercial(self):
        i, f = date(2024, 5, 11), date(2024, 5, 12)
        self.assertFalse(cal.instante_no_periodo(utc(2024, 5, 11, 2, 59, 59), i, f))
        self.assertTrue(cal.instante_no_periodo(utc(2024, 5, 11, 3), i, f))
        self.assertTrue(cal.instante_no_periodo(utc(2024, 5, 12, 2, 59, 59), i, f))
        self.assertFalse(cal.instante_no_periodo(utc(2024, 5, 12, 3), i, f))

    def test_periodo_invalido_ou_invertido(self):
        with self.assertRaises(ValueError):
            cal.periodo_comercial(date(2024, 6, 1), date(2024, 5, 1))
        with self.assertRaises(ValueError):
            cal.periodo_comercial(date(2024, 5, 1), date(2024, 5, 1))

    def test_fim_exclusivo_utc(self):
        self.assertEqual(cal.fim_exclusivo_utc(date(2024, 6, 10)), utc(2024, 6, 10, 3))

    def test_instantes_consecutivos_entre_ciclos_sem_lacuna(self):
        a = cal.periodo_comercial(date(2024, 1, 31), date(2024, 2, 29))
        b = cal.periodo_comercial(date(2024, 2, 29), date(2024, 3, 29))
        self.assertEqual(a.fim, b.inicio)


class HorarioDeVeraoHistoricoTest(unittest.TestCase):
    def test_inicio_do_horario_de_verao_2018(self):
        # 00:00 de 04/11/2018 nao existiu; o dia comeca na transicao (03:00Z).
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2018, 11, 3)), utc(2018, 11, 3, 3))
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2018, 11, 4)), utc(2018, 11, 4, 3))
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2018, 11, 5)), utc(2018, 11, 5, 2))
        self.assertEqual(cal.data_comercial(utc(2018, 11, 4, 3)), date(2018, 11, 4))
        self.assertEqual(cal.data_comercial(utc(2018, 11, 4, 2, 59, 59)), date(2018, 11, 3))

    def test_fim_do_horario_de_verao_2019(self):
        # O dia 16/02/2019 teve 25 horas.
        ini = cal.inicio_dia_comercial_utc(date(2019, 2, 16))
        fim = cal.inicio_dia_comercial_utc(date(2019, 2, 17))
        self.assertEqual(fim - ini, timedelta(hours=25))
        self.assertEqual(ini, utc(2019, 2, 16, 2))

    def test_offset_nao_e_fixo(self):
        offsets = {
            cal.inicio_dia_comercial_utc(date(2018, 12, 15)).hour,
            cal.inicio_dia_comercial_utc(date(2018, 6, 15)).hour,
            cal.inicio_dia_comercial_utc(date(2024, 12, 15)).hour,
        }
        self.assertEqual(offsets, {2, 3})

    def test_periodo_que_cruza_transicao(self):
        p = cal.periodo_comercial(date(2018, 10, 4), date(2018, 11, 4))
        self.assertEqual(p.fim, utc(2018, 11, 4, 3))
        self.assertTrue(cal.instante_no_periodo(utc(2018, 11, 4, 2, 59), date(2018, 10, 4), date(2018, 11, 4)))
        self.assertFalse(cal.instante_no_periodo(utc(2018, 11, 4, 3), date(2018, 10, 4), date(2018, 11, 4)))

    def test_ida_e_volta_em_dias_sem_ambiguidade(self):
        dia = date(2018, 12, 1)
        while dia < date(2019, 3, 1):
            self.assertEqual(cal.data_comercial(cal.inicio_dia_comercial_utc(dia)), dia, dia)
            dia += timedelta(days=1)


class CicloMensalTest(unittest.TestCase):
    def test_avanco_mensal(self):
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 1, 15), "MENSAL"), date(2024, 2, 15))
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 4, 30), "mensal"), date(2024, 5, 30))

    def test_virada_do_mes_dia_31(self):
        self.assertEqual(cal.proxima_data_ciclo(date(2023, 1, 31), "MENSAL"), date(2023, 2, 28))
        self.assertEqual(cal.proxima_data_ciclo(date(2023, 3, 31), "MENSAL"), date(2023, 4, 30))

    def test_fevereiro_bissexto(self):
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 1, 31), "MENSAL"), date(2024, 2, 29))
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 2, 29), "MENSAL"), date(2024, 3, 29))
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 2, 29), "ANUAL"), date(2025, 2, 28))
        self.assertEqual(cal.proxima_data_ciclo(date(2023, 2, 28), "MENSAL"), date(2023, 3, 28))

    def test_dezembro_para_janeiro(self):
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 12, 31), "MENSAL"), date(2025, 1, 31))
        self.assertEqual(cal.proxima_data_ciclo(date(2024, 12, 15), "MENSAL"), date(2025, 1, 15))

    def test_periodicidade_invalida(self):
        with self.assertRaises(ValueError):
            cal.proxima_data_ciclo(date(2024, 1, 1), "SEMANAL")

    def test_renovacao_na_virada_do_mes(self):
        ini = date(2024, 12, 31)
        fim = cal.proxima_data_ciclo(ini, "MENSAL")
        self.assertTrue(cal.instante_no_periodo(utc(2025, 1, 31, 2, 59, 59), ini, fim))
        self.assertFalse(cal.instante_no_periodo(utc(2025, 1, 31, 3), ini, fim))
        prox = cal.proxima_data_ciclo(fim, "MENSAL")
        self.assertTrue(cal.instante_no_periodo(utc(2025, 1, 31, 3), fim, prox))


class ModoEstritoTest(unittest.TestCase):
    INEXISTENTE = datetime(2018, 11, 4, 0, 30)  # 00:00 pulou para 01:00
    AMBIGUO = datetime(2019, 2, 16, 23, 30)  # 23:30 ocorreu duas vezes

    def test_estrito_rejeita_hora_inexistente(self):
        with self.assertRaisesRegex(ValueError, "inexistente"):
            cal.instante_utc(self.INEXISTENTE, SP, estrito=True)

    def test_estrito_rejeita_hora_ambigua(self):
        with self.assertRaisesRegex(ValueError, "ambiguo"):
            cal.instante_utc(self.AMBIGUO, SP, estrito=True)
        with self.assertRaises(ValueError):
            cal.data_comercial(self.AMBIGUO, SP, estrito=True)
        with self.assertRaises(ValueError):
            cal.instante_no_periodo(
                self.AMBIGUO, date(2019, 2, 1), date(2019, 3, 1), SP, estrito=True
            )

    def test_estrito_aceita_hora_unica_e_nao_aplica_offset_fixo(self):
        self.assertEqual(cal.instante_utc(datetime(2018, 12, 15, 12), SP, estrito=True), utc(2018, 12, 15, 14))
        self.assertEqual(cal.instante_utc(datetime(2018, 6, 15, 12), SP, estrito=True), utc(2018, 6, 15, 15))

    def test_estrito_com_utc_nao_tem_ambiguidade(self):
        self.assertEqual(cal.instante_utc(self.AMBIGUO, UTC, estrito=True), utc(2019, 2, 16, 23, 30))
        self.assertEqual(cal.instante_utc(self.INEXISTENTE, "UTC", estrito=True), utc(2018, 11, 4, 0, 30))

    def test_estrito_sem_origem_continua_rejeitando(self):
        with self.assertRaises(ValueError):
            cal.instante_utc(datetime(2024, 5, 10, 12), estrito=True)

    def test_estrito_preserva_instante_com_fuso(self):
        com_fuso = datetime(2019, 2, 16, 23, 30, tzinfo=SP, fold=1)
        self.assertEqual(cal.instante_utc(com_fuso, estrito=True), utc(2019, 2, 17, 2, 30))
        com_fuso = datetime(2019, 2, 16, 23, 30, tzinfo=SP, fold=0)
        self.assertEqual(cal.instante_utc(com_fuso, estrito=True), utc(2019, 2, 17, 1, 30))
        self.assertIs(cal.instante_utc(com_fuso, estrito=True).tzinfo, UTC)

    def test_modo_padrao_preserva_comportamento_anterior(self):
        self.assertEqual(cal.instante_utc(self.AMBIGUO, SP), utc(2019, 2, 17, 1, 30))
        self.assertEqual(cal.instante_utc(self.AMBIGUO, "America/Sao_Paulo"), utc(2019, 2, 17, 1, 30))

    def test_estrito_so_vale_para_keyword(self):
        with self.assertRaises(TypeError):
            cal.instante_utc(self.AMBIGUO, SP, True)


class FusoConfiguravelTest(unittest.TestCase):
    def test_padrao_continua_sao_paulo(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2024, 5, 10)), utc(2024, 5, 10, 3))

    def test_fuso_utc_por_nome_e_por_objeto(self):
        for fuso in ("UTC", UTC):
            self.assertEqual(cal.inicio_dia_comercial_utc(date(2024, 5, 10), fuso=fuso), utc(2024, 5, 10))
            p = cal.periodo_comercial(date(2024, 5, 10), date(2024, 6, 10), fuso=fuso)
            self.assertEqual((p.inicio, p.fim), (utc(2024, 5, 10), utc(2024, 6, 10)))

    def test_fuso_sao_paulo_explicito(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2024, 5, 10), fuso="America/Sao_Paulo"), utc(2024, 5, 10, 3))
        self.assertEqual(cal.fim_exclusivo_utc(date(2024, 5, 10), fuso=SP), utc(2024, 5, 10, 3))

    def test_data_comercial_em_utc_e_sao_paulo(self):
        instante = utc(2024, 5, 11, 1)
        self.assertEqual(cal.data_comercial(instante, fuso="UTC"), date(2024, 5, 11))
        self.assertEqual(cal.data_comercial(instante), date(2024, 5, 10))

    def test_limites_com_fuso_utc(self):
        i, f = date(2024, 5, 10), date(2024, 5, 11)
        self.assertTrue(cal.instante_no_periodo(utc(2024, 5, 10), i, f, fuso="UTC"))
        self.assertFalse(cal.instante_no_periodo(utc(2024, 5, 11), i, f, fuso="UTC"))
        self.assertFalse(cal.instante_no_periodo(utc(2024, 5, 9, 23, 59, 59), i, f, fuso="UTC"))

    def test_fuso_invalido(self):
        with self.assertRaises(ValueError):
            cal.inicio_dia_comercial_utc(date(2024, 5, 10), fuso="Nao/Existe")
        with self.assertRaises(TypeError):
            cal.inicio_dia_comercial_utc(date(2024, 5, 10), fuso=3)

    def test_origem_sem_fuso_nao_tem_padrao(self):
        with self.assertRaises(ValueError):
            cal.instante_utc(datetime(2024, 5, 10, 12), estrito=True)
        self.assertEqual(cal.data_comercial(datetime(2024, 5, 11, 1), "UTC"), date(2024, 5, 10))
        self.assertEqual(cal.data_comercial(datetime(2024, 5, 11, 1), "UTC", fuso="UTC"), date(2024, 5, 11))


class DataCivilEmTransicaoTest(unittest.TestCase):
    def test_inicio_coincide_com_transicao_de_verao(self):
        ini = cal.inicio_dia_comercial_utc(date(2018, 11, 4))
        self.assertEqual(ini, utc(2018, 11, 4, 3))
        self.assertEqual(cal.data_comercial(ini - timedelta(microseconds=1)), date(2018, 11, 3))
        self.assertEqual(cal.data_comercial(ini), date(2018, 11, 4))

    def test_data_civil_nao_interpreta_timestamp_historico(self):
        # A mesma regra nao e aplicada a timestamp sem fuso: continua rejeitado.
        with self.assertRaises(ValueError):
            cal.instante_utc(datetime(2018, 11, 4, 0, 30), SP, estrito=True)
        with self.assertRaises(ValueError):
            cal.instante_utc(datetime(2018, 11, 4, 0, 30))

    def test_dia_do_fim_do_verao_comeca_na_primeira_ocorrencia(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2019, 2, 16)), utc(2019, 2, 16, 2))

    def test_utc_nunca_tem_lacuna(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2018, 11, 4), fuso="UTC"), utc(2018, 11, 4))


class DataCivilEstritaTest(unittest.TestCase):
    def test_meia_noite_inexistente_rejeitada_no_estrito(self):
        with self.assertRaisesRegex(ValueError, "inexistente"):
            cal.inicio_dia_comercial_utc(date(2018, 11, 4), estrito=True)
        with self.assertRaises(ValueError):
            cal.periodo_comercial(date(2018, 10, 4), date(2018, 11, 4), estrito=True)
        with self.assertRaises(ValueError):
            cal.periodo_comercial(date(2018, 11, 4), date(2018, 12, 4), estrito=True)
        with self.assertRaises(ValueError):
            cal.fim_exclusivo_utc(date(2018, 11, 4), estrito=True)
        with self.assertRaises(ValueError):
            cal.instante_no_periodo(utc(2018, 11, 10), date(2018, 11, 4), date(2018, 12, 4), estrito=True)

    def test_padrao_continua_resolvendo_a_transicao(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2018, 11, 4)), utc(2018, 11, 4, 3))
        self.assertEqual(cal.periodo_comercial(date(2018, 10, 4), date(2018, 11, 4)).fim, utc(2018, 11, 4, 3))

    def test_dia_comum_igual_nos_dois_modos(self):
        for dia in (date(2024, 5, 10), date(2018, 12, 15), date(2019, 2, 16)):
            self.assertEqual(
                cal.inicio_dia_comercial_utc(dia, estrito=True), cal.inicio_dia_comercial_utc(dia)
            )

    def test_estrito_com_utc_e_fuso_explicito(self):
        self.assertEqual(cal.inicio_dia_comercial_utc(date(2018, 11, 4), fuso="UTC", estrito=True), utc(2018, 11, 4))
        with self.assertRaises(ValueError):
            cal.inicio_dia_comercial_utc(date(2018, 11, 4), fuso=SP, estrito=True)

    def test_estrito_so_por_keyword(self):
        with self.assertRaises(TypeError):
            cal.inicio_dia_comercial_utc(date(2018, 11, 4), None, True)

    def test_estrito_rejeita_datetime(self):
        with self.assertRaises(TypeError):
            cal.inicio_dia_comercial_utc(datetime(2018, 11, 4), estrito=True)


class IndependenciaDoSistemaTest(unittest.TestCase):
    CODIGO = (
        "from datetime import date, datetime, timezone;"
        "from app.tenant import commercial_calendar as c;"
        "p=c.periodo_comercial(date(2024,5,10),date(2024,6,10));"
        "print(p.inicio.isoformat(),p.fim.isoformat(),"
        "c.data_comercial(datetime(2024,5,11,2,59,tzinfo=timezone.utc)),"
        "c.data_comercial(datetime(2024,5,11,3,0,tzinfo=timezone.utc)))"
    )

    def _rodar(self, tz):
        env = dict(os.environ, TZ=tz, PYTHONPATH=str(RAIZ))
        r = subprocess.run([sys.executable, "-c", self.CODIGO], env=env, cwd=RAIZ,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_resultado_igual_em_varios_fusos_do_sistema(self):
        saidas = {self._rodar(tz) for tz in ("UTC", "Asia/Tokyo", "America/Sao_Paulo", "Pacific/Auckland")}
        self.assertEqual(len(saidas), 1, saidas)
        self.assertIn("2024-05-10T03:00:00+00:00", saidas.pop())

    def test_modulo_nao_usa_relogio_do_sistema(self):
        fonte = (RAIZ / "app" / "tenant" / "commercial_calendar.py").read_text(encoding="utf-8")
        for proibido in ("today(", ".now(", "utcnow", "time.tzset", "environ"):
            self.assertNotIn(proibido, fonte)


class ConsistenciaComPoliticaTest(unittest.TestCase):
    def test_periodo_e_valido_para_a_politica(self):
        p = cal.periodo_comercial(date(2024, 5, 10), date(2024, 6, 10))
        self.assertIs(type(p), pol.Periodo)
        self.assertTrue(pol._periodo(p))
        self.assertIs(p.inicio.tzinfo, timezone.utc)
        self.assertIs(p.fim.tzinfo, timezone.utc)

    def test_semantica_de_limites_igual_a_da_politica(self):
        p = cal.periodo_comercial(date(2024, 5, 10), date(2024, 6, 10))
        self.assertTrue(pol._contem(p, p.inicio))
        self.assertFalse(pol._contem(p, p.fim))
        self.assertFalse(pol._contem(p, p.inicio - timedelta(microseconds=1)))
        self.assertTrue(pol._contem(p, p.fim - timedelta(microseconds=1)))

    def test_periodo_invertido_tambem_e_invalido_na_politica(self):
        self.assertFalse(pol._periodo(pol.Periodo(utc(2024, 6, 1), utc(2024, 5, 1))))


if __name__ == "__main__":
    unittest.main()
