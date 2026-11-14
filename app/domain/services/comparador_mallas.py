"""Compara cuánto le falta a un estudiante en su malla de origen y en la vigente.

En la malla de ORIGEN se cuenta como lo hace la universidad en su reporte:
- obligatorias y nivelación: materia por materia (por código);
- optativas y libre elección: por bolsa de créditos (lo aprobado de esa
  tipología contra lo exigido).

En la malla DESTINO se usa el motor de transición (con sus cupos y tickets).
El resultado es una estimación para orientar la decisión, no un certificado.
"""
from __future__ import annotations

from dataclasses import replace

from app.domain.entities import (
    ComparacionMallas,
    Equivalencia,
    EstadoMateria,
    Estudiante,
    Malla,
    MateriaCatalogo,
    TipoMateria,
)
from app.domain.services.motor_transicion import MotorTransicion, separar_historial


def comparar_mallas(
    estudiante: Estudiante,
    malla_origen: Malla,
    malla_destino: Malla,
    motor: MotorTransicion,
    equivalencias: list[Equivalencia],
    catalogo: list[MateriaCatalogo],
) -> ComparacionMallas:
    def destino(proyectado: bool) -> int:
        return motor.evaluar(estudiante, malla_destino, equivalencias, catalogo, proyectado).creditos_pendientes

    return ComparacionMallas(
        malla_origen=malla_origen.version,
        malla_destino=malla_destino.version,
        pendientes_origen=pendientes_en_origen(estudiante, malla_origen, catalogo, False),
        pendientes_destino=destino(False),
        pendientes_origen_proyectado=pendientes_en_origen(estudiante, malla_origen, catalogo, True),
        pendientes_destino_proyectado=destino(True),
    )


def pendientes_en_origen(
    estudiante: Estudiante,
    malla: Malla,
    catalogo: list[MateriaCatalogo],
    incluir_cursando: bool,
) -> int:
    aprobadas, _, cursando = separar_historial(estudiante.materias_vistas)
    if incluir_cursando:
        aprobadas += [replace(v, estado=EstadoMateria.APROBADA) for v in cursando]

    codigos_aprobados = {v.codigo for v in aprobadas}
    en_catalogo = {c.codigo for c in catalogo}
    concretas = {m.codigo for m in malla.materias if not m.es_cupo}

    pendientes_concretas = sum(
        m.creditos for m in malla.materias
        if not m.es_cupo and m.codigo not in codigos_aprobados
    )

    optativas = electivas = 0
    for vista in aprobadas:
        if vista.codigo in concretas:
            continue
        tipologia = vista.tipologia
        if "optativa" in tipologia or (not tipologia and vista.codigo in en_catalogo):
            optativas += vista.creditos
        elif "libre" in tipologia or not tipologia:
            electivas += vista.creditos

    falta_optativas = max(malla.creditos_por_tipo(TipoMateria.OPTATIVA) - optativas, 0)
    falta_electivas = max(malla.creditos_por_tipo(TipoMateria.ELECTIVA) - electivas, 0)
    return pendientes_concretas + falta_optativas + falta_electivas
