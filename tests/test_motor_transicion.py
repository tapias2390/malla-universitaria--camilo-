"""Pruebas de las reglas de transición de malla (dominio puro, sin archivos)."""
from app.domain.entities import (
    Estudiante,
    Malla,
    Materia,
    MateriaVista,
    TipoHomologacion,
    TipoMateria,
)
from app.domain.services.motor_transicion import MotorTransicion

OB, EL = TipoMateria.OBLIGATORIA, TipoMateria.ELECTIVA


def malla_2025(*electivas: Materia) -> Malla:
    return Malla("2025", [
        Materia("MAT101", "Cálculo I", 4, 1, OB),
        Materia("BDD201", "Bases de datos", 3, 3, OB),
        *electivas,
    ])


def estudiante(*vistas: MateriaVista, malla: str = "2020") -> Estudiante:
    return Estudiante("E1", "Prueba", "123", malla, "activo", list(vistas))


def vista(codigo: str, creditos: int = 3, nota: float = 4.0) -> MateriaVista:
    return MateriaVista(codigo, codigo, creditos, nota, "2023-1")


def tipos(resultado) -> dict[str, TipoHomologacion]:
    return {h.materia_vista.codigo: h.tipo for h in resultado.homologaciones}


motor = MotorTransicion(nota_minima=3.0)


def test_materia_que_sigue_existiendo_se_homologa_directa():
    r = motor.evaluar(estudiante(vista("MAT101", 4)), malla_2025())
    assert tipos(r) == {"MAT101": TipoHomologacion.DIRECTA}
    assert r.creditos_reconocidos == 4


def test_equivalencia_por_cambio_de_codigo():
    r = motor.evaluar(estudiante(vista("BD201")), malla_2025(), {"BD201": "BDD201"})
    assert tipos(r) == {"BD201": TipoHomologacion.EQUIVALENCIA}
    assert r.homologaciones[0].materia_destino.codigo == "BDD201"


def test_materia_eliminada_ocupa_una_electiva():
    r = motor.evaluar(estudiante(vista("FIS101", 4)), malla_2025(Materia("ELE01", "Electiva I", 3, 4, EL)))
    assert tipos(r) == {"FIS101": TipoHomologacion.REEMPLAZO_ELECTIVA}
    assert all(m.codigo != "ELE01" for m in r.materias_pendientes)


def test_sin_electivas_requiere_revision():
    r = motor.evaluar(estudiante(vista("FIS101", 4)), malla_2025())
    assert tipos(r) == {"FIS101": TipoHomologacion.REQUIERE_REVISION}
    assert len(r.casos_revision) == 1


def test_electiva_con_mas_creditos_que_la_vista_no_se_usa():
    # La materia vista tiene 2 créditos; la electiva pide 3 -> no cumple los créditos.
    r = motor.evaluar(estudiante(vista("HUM101", 2)), malla_2025(Materia("ELE01", "Electiva I", 3, 4, EL)))
    assert tipos(r) == {"HUM101": TipoHomologacion.REQUIERE_REVISION}


def test_cupos_de_electiva_agotados_generan_revision():
    malla = malla_2025(Materia("ELE01", "Electiva I", 3, 4, EL))
    r = motor.evaluar(estudiante(vista("FIS101", 4), vista("QUI101", 3)), malla)
    t = tipos(r)
    # La de más créditos se procesa primero y se queda con la electiva.
    assert t["FIS101"] is TipoHomologacion.REEMPLAZO_ELECTIVA
    assert t["QUI101"] is TipoHomologacion.REQUIERE_REVISION


def test_se_elige_la_electiva_que_menos_creditos_desperdicia():
    malla = malla_2025(Materia("ELE01", "Electiva I", 2, 4, EL), Materia("ELE02", "Electiva II", 3, 5, EL))
    r = motor.evaluar(estudiante(vista("FIS101", 3)), malla)
    assert r.homologaciones[0].materia_destino.codigo == "ELE02"


def test_reprobadas_no_cuentan_y_se_toma_el_mejor_intento():
    r = motor.evaluar(
        estudiante(vista("MAT101", 4, nota=2.0), vista("MAT101", 4, nota=3.5), vista("BDD201", nota=1.0)),
        malla_2025(),
    )
    assert tipos(r) == {"MAT101": TipoHomologacion.DIRECTA}
    assert [v.codigo for v in r.materias_no_aprobadas] == ["BDD201"]


def test_estudiante_nuevo_no_requiere_transicion():
    r = motor.evaluar(estudiante(vista("MAT101", 4), malla="2025"), malla_2025())
    assert r.requiere_transicion is False
    assert r.creditos_pendientes == 3
