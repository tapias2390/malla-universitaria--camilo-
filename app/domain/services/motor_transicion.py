"""Motor de transición de malla: el corazón de las reglas de negocio.

Reglas que aplica (en este orden):

1. Solo cuentan las materias APROBADAS (nota >= nota mínima). Si una materia
   se cursó varias veces, se toma el intento con la mejor nota.
2. Si la materia aprobada existe con el mismo código en la malla nueva
   -> homologación DIRECTA.
3. Si no existe pero hay una equivalencia registrada (código anterior -> código
   nuevo) -> homologación por EQUIVALENCIA.
4. Si la materia fue eliminada de la malla nueva -> se usa para llenar un cupo de
   ELECTIVA libre. Para cumplir con los créditos, la electiva elegida no puede
   tener más créditos que la materia vista (no se regalan créditos). Se elige la
   electiva con más créditos que cumpla esa condición (la que menos créditos
   "desperdicia").
5. Si no queda ninguna electiva que cumpla -> REQUIERE_REVISION (se generará un
   ticket para que alguien revise el caso).

Las materias eliminadas se procesan de mayor a menor número de créditos, para
que las de más créditos tengan prioridad sobre los cupos de electiva grandes.

Este módulo es puro: no lee archivos ni crea tickets; solo decide.
"""
from __future__ import annotations

from app.domain.entities import (
    Estudiante,
    Homologacion,
    Malla,
    Materia,
    MateriaVista,
    ResultadoTransicion,
    TipoHomologacion,
)


class MotorTransicion:
    def __init__(self, nota_minima: float = 3.0) -> None:
        self._nota_minima = nota_minima

    def evaluar(
        self,
        estudiante: Estudiante,
        malla_vigente: Malla,
        equivalencias: dict[str, str] | None = None,
    ) -> ResultadoTransicion:
        """Calcula cómo queda el estudiante en la malla vigente.

        :param equivalencias: diccionario {codigo_anterior: codigo_nuevo}.
        """
        equivalencias = equivalencias or {}

        aprobadas, no_aprobadas = self._separar_por_resultado(estudiante.materias_vistas)

        # Códigos de la malla nueva que ya quedaron cubiertos por alguna materia vista.
        # Evita que dos materias vistas ocupen el mismo lugar.
        cubiertas: set[str] = set()
        homologaciones: list[Homologacion] = []
        eliminadas: list[MateriaVista] = []

        # --- Pasos 2 y 3: coincidencia directa o por equivalencia -----------------
        # Se hacen primero para que una materia que sí existe nunca consuma un
        # cupo de electiva.
        for vista in aprobadas:
            homologacion = self._homologar_directa_o_equivalente(
                vista, malla_vigente, equivalencias, cubiertas
            )
            if homologacion:
                homologaciones.append(homologacion)
                cubiertas.add(homologacion.materia_destino.codigo)
            else:
                eliminadas.append(vista)

        # --- Pasos 4 y 5: materias eliminadas -> electiva o revisión --------------
        for vista in sorted(eliminadas, key=lambda m: m.creditos, reverse=True):
            electiva = self._elegir_electiva(vista, malla_vigente, cubiertas)
            if electiva:
                cubiertas.add(electiva.codigo)
                homologaciones.append(
                    Homologacion(
                        materia_vista=vista,
                        tipo=TipoHomologacion.REEMPLAZO_ELECTIVA,
                        materia_destino=electiva,
                        observacion=(
                            f"'{vista.nombre}' fue eliminada de la malla {malla_vigente.version}; "
                            f"se reconoce como '{electiva.nombre}' ({electiva.creditos} créditos)."
                        ),
                    )
                )
            else:
                homologaciones.append(
                    Homologacion(
                        materia_vista=vista,
                        tipo=TipoHomologacion.REQUIERE_REVISION,
                        materia_destino=None,
                        observacion=self._motivo_sin_electiva(vista, malla_vigente, cubiertas),
                    )
                )

        pendientes = [m for m in malla_vigente.materias if m.codigo not in cubiertas]

        return ResultadoTransicion(
            estudiante=estudiante,
            malla_destino=malla_vigente,
            requiere_transicion=estudiante.malla_version != malla_vigente.version,
            homologaciones=homologaciones,
            materias_pendientes=sorted(pendientes, key=lambda m: (m.semestre, m.codigo)),
            materias_no_aprobadas=no_aprobadas,
        )

    # ------------------------------------------------------------------ helpers
    def _separar_por_resultado(
        self, vistas: list[MateriaVista]
    ) -> tuple[list[MateriaVista], list[MateriaVista]]:
        """Devuelve (aprobadas, no_aprobadas), quedándose con el mejor intento por materia."""
        mejor_intento: dict[str, MateriaVista] = {}
        for vista in vistas:
            actual = mejor_intento.get(vista.codigo)
            if actual is None or vista.nota > actual.nota:
                mejor_intento[vista.codigo] = vista

        aprobadas = [v for v in mejor_intento.values() if v.aprobada(self._nota_minima)]
        no_aprobadas = [v for v in mejor_intento.values() if not v.aprobada(self._nota_minima)]
        return aprobadas, no_aprobadas

    @staticmethod
    def _homologar_directa_o_equivalente(
        vista: MateriaVista,
        malla: Malla,
        equivalencias: dict[str, str],
        cubiertas: set[str],
    ) -> Homologacion | None:
        directa = malla.buscar(vista.codigo)
        if directa and directa.codigo not in cubiertas:
            return Homologacion(
                materia_vista=vista,
                tipo=TipoHomologacion.DIRECTA,
                materia_destino=directa,
                observacion="La materia se mantiene en la malla vigente.",
            )

        codigo_nuevo = equivalencias.get(vista.codigo)
        equivalente = malla.buscar(codigo_nuevo) if codigo_nuevo else None
        if equivalente and equivalente.codigo not in cubiertas:
            return Homologacion(
                materia_vista=vista,
                tipo=TipoHomologacion.EQUIVALENCIA,
                materia_destino=equivalente,
                observacion=f"Equivale a '{equivalente.nombre}' ({equivalente.codigo}).",
            )
        return None

    @staticmethod
    def _elegir_electiva(
        vista: MateriaVista, malla: Malla, cubiertas: set[str]
    ) -> Materia | None:
        """Electiva libre con créditos <= a los de la materia vista; la de más créditos."""
        candidatas = [
            e for e in malla.electivas
            if e.codigo not in cubiertas and e.creditos <= vista.creditos
        ]
        if not candidatas:
            return None
        # Más créditos primero; a igualdad, la de semestre más bajo y luego por código.
        return min(candidatas, key=lambda e: (-e.creditos, e.semestre, e.codigo))

    @staticmethod
    def _motivo_sin_electiva(vista: MateriaVista, malla: Malla, cubiertas: set[str]) -> str:
        libres = [e for e in malla.electivas if e.codigo not in cubiertas]
        if not malla.electivas:
            causa = f"la malla {malla.version} no tiene electivas"
        elif not libres:
            causa = "todos los cupos de electiva ya están ocupados"
        else:
            causa = (
                f"las electivas libres tienen más créditos ({min(e.creditos for e in libres)}+) "
                f"que la materia vista ({vista.creditos})"
            )
        return (
            f"'{vista.nombre}' fue eliminada de la malla {malla.version} y no se pudo "
            f"reemplazar por una electiva: {causa}. Requiere revisión."
        )
