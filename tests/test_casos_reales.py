"""Casos reales (anonimizados) de Ingeniería Química con las mallas 2016 y 2026.

Las cifras esperadas salen del análisis manual de las historias académicas y
coinciden con el "resumen de créditos" que reporta la universidad.
"""
import pytest

from app.domain.entities import TipoHomologacion as TH
from app.domain.services.comparador_mallas import comparar_mallas
from app.domain.services.motor_transicion import MotorTransicion
from app.infrastructure.data_sources.fuentes import FuenteLocal
from app.infrastructure.repositories.excel_academico import ExcelRepositorioAcademico

PRUEBA1, PRUEBA2, PRUEBA3 = "20242001", "20221001", "20261001"


@pytest.fixture(scope="module")
def repo(datos_dir):
    return ExcelRepositorioAcademico(FuenteLocal(datos_dir / "academico.xlsx"))


@pytest.fixture(scope="module")
def evaluar(repo):
    motor = MotorTransicion()
    eq, cat = repo.obtener_equivalencias(), repo.obtener_catalogo_optativas()
    m16, m26 = repo.obtener_malla("2016"), repo.obtener_malla("2026")

    def _evaluar(codigo):
        e = repo.obtener_estudiante(codigo)
        return motor.evaluar(e, m26, eq, cat), comparar_mallas(e, m16, m26, motor, eq, cat)

    return _evaluar


def tipo_de(resultado, codigo):
    return next(h.tipo for h in resultado.homologaciones if h.materia_vista.codigo == codigo)


def test_mallas_reales_cuadran_con_los_creditos_oficiales(repo):
    assert repo.obtener_malla("2016").creditos_totales == 192   # 144 + 36 libre elección + 12 nivelación
    assert repo.obtener_malla("2026").creditos_totales == 178   # 133 + 33 libre elección + 12 nivelación


def test_prueba1_estudiante_en_curso(evaluar):
    r, c = evaluar(PRUEBA1)
    assert r.creditos_reconocidos == 49
    assert r.creditos_cursando == 19
    # Inglés por suficiencia (sin nota) sí cuenta
    assert tipo_de(r, "1000044") is TH.DIRECTA
    # Química General I + II se fusionan en Química General
    assert tipo_de(r, "4100839") is TH.EQUIVALENCIA and tipo_de(r, "4100840") is TH.EQUIVALENCIA
    # Programación sin Métodos Numéricos: fusión incompleta
    assert tipo_de(r, "4100925") is TH.REQUIERE_REVISION
    # Optativas del catálogo
    assert tipo_de(r, "4100684") is TH.OPTATIVA and tipo_de(r, "4100584") is TH.OPTATIVA
    # Materias de 2 créditos sin cupo de libre elección de 2 -> revisión
    assert {h.materia_vista.codigo for h in r.casos_revision} == {"4100925", "1000089", "4100921", "4100926"}
    # Pendientes en la malla 2016 = lo que reporta la universidad
    assert c.pendientes_origen == 132
    assert c.conviene_transicion


def test_prueba2_estudiante_avanzada_no_le_conviene_la_transicion(evaluar):
    r, c = evaluar(PRUEBA2)
    assert r.creditos_pendientes == 30
    # Física E&M la vio como optativa, pero en 2026 es obligatoria con el mismo código
    assert tipo_de(r, "1000017") is TH.DIRECTA
    # Los 11 cupos de libre elección quedan llenos
    assert next(x for x in r.resumen_por_tipo() if x.tipo.value == "electiva").pendientes == 0
    assert c.pendientes_origen == 34                 # igual al reporte oficial
    assert (c.pendientes_origen_proyectado, c.pendientes_destino_proyectado) == (19, 21)
    assert not c.conviene_transicion


def test_prueba3_ya_esta_en_la_malla_vigente(evaluar):
    r, _ = evaluar(PRUEBA3)
    assert r.requiere_transicion is False
    assert r.creditos_reconocidos == 17
    assert r.casos_revision == []
