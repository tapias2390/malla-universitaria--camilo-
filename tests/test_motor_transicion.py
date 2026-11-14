"""Pruebas de las reglas de transición de malla (dominio puro, sin archivos)."""
from app.domain.entities import (
    Equivalencia,
    EstadoMateria,
    Estudiante,
    Malla,
    Materia,
    MateriaCatalogo,
    MateriaVista,
    TipoHomologacion,
    TipoMateria,
)
from app.domain.services.motor_transicion import MotorTransicion

OB, EL, OP = TipoMateria.OBLIGATORIA, TipoMateria.ELECTIVA, TipoMateria.OPTATIVA
TH = TipoHomologacion
motor = MotorTransicion()


def malla_nueva(*extra: Materia) -> Malla:
    return Malla("2026", [
        Materia("MAT101", "Cálculo I", 4, 1, OB),
        Materia("BDD201", "Bases de datos", 3, 3, OB),
        *extra,
    ])


def estudiante(*vistas: MateriaVista, malla: str = "2016") -> Estudiante:
    return Estudiante("E1", "Prueba", "123", malla, "activo", materias_vistas=list(vistas))


def vista(codigo: str, creditos: int = 3, nota: float | None = 4.0,
          estado: EstadoMateria = EstadoMateria.APROBADA, tipologia: str = "") -> MateriaVista:
    return MateriaVista(codigo, codigo, creditos, nota, "2023-1", estado, tipologia)


def tipos(resultado) -> dict[str, TipoHomologacion]:
    return {h.materia_vista.codigo: h.tipo for h in resultado.homologaciones}


def electiva(codigo: str, creditos: int = 3) -> Materia:
    return Materia(codigo, f"Libre elección {codigo}", creditos, 5, EL)


# ------------------------------------------------------------------ reglas básicas
def test_materia_que_sigue_existiendo_se_homologa_directa():
    r = motor.evaluar(estudiante(vista("MAT101", 4)), malla_nueva())
    assert tipos(r) == {"MAT101": TH.DIRECTA}
    assert r.creditos_reconocidos == 4


def test_directa_con_cambio_de_creditos_lo_indica():
    r = motor.evaluar(estudiante(vista("MAT101", 3)), malla_nueva())
    assert "vale 4 créditos (la vio con 3)" in r.homologaciones[0].observacion


def test_equivalencia_por_cambio_de_codigo():
    r = motor.evaluar(estudiante(vista("BD201")), malla_nueva(), [Equivalencia("BD201", "BDD201")])
    assert tipos(r) == {"BD201": TH.EQUIVALENCIA}
    assert r.homologaciones[0].materia_destino.codigo == "BDD201"


def test_materia_eliminada_ocupa_una_electiva_de_igual_o_menos_creditos():
    r = motor.evaluar(estudiante(vista("FIS101", 4)), malla_nueva(electiva("LE-01", 3)))
    assert tipos(r) == {"FIS101": TH.REEMPLAZO_ELECTIVA}
    assert all(m.codigo != "LE-01" for m in r.materias_pendientes)


def test_sin_electivas_requiere_revision():
    r = motor.evaluar(estudiante(vista("FIS101", 4)), malla_nueva())
    assert tipos(r) == {"FIS101": TH.REQUIERE_REVISION}
    assert len(r.casos_revision) == 1


def test_electiva_con_mas_creditos_que_la_vista_no_se_usa():
    # La materia vista tiene 2 créditos; el cupo pide 3 -> no cumple los créditos.
    r = motor.evaluar(estudiante(vista("HUM101", 2)), malla_nueva(electiva("LE-01", 3)))
    assert tipos(r) == {"HUM101": TH.REQUIERE_REVISION}


def test_cupos_de_electiva_agotados_generan_revision():
    r = motor.evaluar(estudiante(vista("FIS101", 4), vista("QUI101", 3)), malla_nueva(electiva("LE-01", 3)))
    t = tipos(r)
    # La de más créditos se procesa primero y se queda con el cupo.
    assert t["FIS101"] is TH.REEMPLAZO_ELECTIVA
    assert t["QUI101"] is TH.REQUIERE_REVISION


def test_se_elige_la_electiva_que_menos_creditos_desperdicia():
    r = motor.evaluar(estudiante(vista("FIS101", 3)), malla_nueva(electiva("LE-01", 2), electiva("LE-02", 3)))
    assert r.homologaciones[0].materia_destino.codigo == "LE-02"


# ------------------------------------------------------------------ historial
def test_reprobadas_no_cuentan_y_se_toma_el_mejor_intento():
    r = motor.evaluar(
        estudiante(
            vista("MAT101", 4, 2.0, EstadoMateria.REPROBADA),
            vista("MAT101", 4, 3.5),
            vista("BDD201", 3, 1.0, EstadoMateria.REPROBADA),
        ),
        malla_nueva(),
    )
    assert tipos(r) == {"MAT101": TH.DIRECTA}
    assert [v.codigo for v in r.materias_no_aprobadas] == ["BDD201"]


def test_aprobada_sin_nota_por_suficiencia_cuenta():
    r = motor.evaluar(estudiante(vista("MAT101", 4, nota=None)), malla_nueva())
    assert tipos(r) == {"MAT101": TH.DIRECTA}


def test_materias_en_curso_no_cuentan_pero_se_proyectan():
    e = estudiante(vista("MAT101", 4, None, EstadoMateria.CURSANDO))
    r = motor.evaluar(e, malla_nueva())
    assert r.homologaciones == [] and r.creditos_cursando == 4
    proyectado = motor.evaluar(e, malla_nueva(), incluir_cursando=True)
    assert proyectado.creditos_reconocidos == 4


def test_canceladas_se_ignoran():
    r = motor.evaluar(estudiante(vista("MAT101", 4, None, EstadoMateria.CANCELADA)), malla_nueva())
    assert r.homologaciones == [] and r.materias_no_aprobadas == [] and r.materias_cursando == []


def test_estudiante_nuevo_no_requiere_transicion():
    r = motor.evaluar(estudiante(vista("MAT101", 4), malla="2026"), malla_nueva())
    assert r.requiere_transicion is False
    assert r.creditos_pendientes == 3


# ------------------------------------------------------------------ fusiones
FUSION = [Equivalencia("QG1", "QG"), Equivalencia("QG2", "QG")]


def test_fusion_completa_cuenta_una_sola_vez():
    malla = malla_nueva(Materia("QG", "Química General", 3, 1, OB))
    r = motor.evaluar(estudiante(vista("QG1"), vista("QG2")), malla, FUSION)
    assert tipos(r) == {"QG1": TH.EQUIVALENCIA, "QG2": TH.EQUIVALENCIA}
    assert r.creditos_reconocidos == 3          # no 6: la fusión cubre una sola materia


def test_fusion_incompleta_va_a_revision():
    malla = malla_nueva(Materia("QG", "Química General", 3, 1, OB), electiva("LE-01", 3))
    r = motor.evaluar(estudiante(vista("QG1")), malla, FUSION)
    assert tipos(r) == {"QG1": TH.REQUIERE_REVISION}
    assert "QG2" in r.homologaciones[0].observacion
    assert any(m.codigo == "QG" for m in r.materias_pendientes)


# ------------------------------------------------------------------ optativas
def test_materia_del_catalogo_llena_cupo_de_optativa_de_su_grupo():
    malla = malla_nueva(Materia("OPT-1", "Optativa", 3, 6, OP, grupo="disciplinar"), electiva("LE-01", 3))
    catalogo = [MateriaCatalogo("disciplinar", "HIG", "Higiene")]
    r = motor.evaluar(estudiante(vista("HIG", 3)), malla, catalogo=catalogo)
    assert tipos(r) == {"HIG": TH.OPTATIVA}
    assert r.homologaciones[0].materia_destino.codigo == "OPT-1"


def test_optativa_de_otro_grupo_no_se_usa():
    malla = malla_nueva(Materia("OPT-1", "Optativa", 3, 6, OP, grupo="ciencias_sociales"), electiva("LE-01", 3))
    catalogo = [MateriaCatalogo("disciplinar", "HIG", "Higiene")]
    r = motor.evaluar(estudiante(vista("HIG", 3)), malla, catalogo=catalogo)
    assert tipos(r) == {"HIG": TH.REEMPLAZO_ELECTIVA}


def test_materia_de_libre_eleccion_va_a_cupo_de_libre_eleccion():
    r = motor.evaluar(estudiante(vista("CATEDRA", 3, tipologia="libre_eleccion")), malla_nueva(electiva("LE-01", 3)))
    assert tipos(r) == {"CATEDRA": TH.REEMPLAZO_ELECTIVA}
    assert "libre elección" in r.homologaciones[0].observacion.lower()


def test_resumen_por_tipo():
    malla = malla_nueva(electiva("LE-01", 3))
    r = motor.evaluar(estudiante(vista("MAT101", 4), vista("X", 3)), malla)
    resumen = {x.tipo: (x.reconocidos, x.requeridos) for x in r.resumen_por_tipo()}
    assert resumen[OB] == (4, 7) and resumen[EL] == (3, 3)
