"""Motor de transición de malla: el corazón de las reglas de negocio.

Objetivo: pasar a cada estudiante a la malla vigente y verificar que cumpla los
créditos. Para cada materia que el estudiante APROBÓ se busca dónde queda en la
malla nueva, en este orden:

1. DIRECTA       La materia existe con el mismo código en la malla nueva.
2. EQUIVALENCIA  Hay una equivalencia registrada (cambio de código). Si varias
                 materias anteriores apuntan a la misma nueva es una FUSIÓN y se
                 exigen todas; si falta alguna, el caso va a revisión.
3. OPTATIVA      La materia está en el catálogo de optativas y hay un cupo de
                 optativa de ese grupo con créditos <= a los de la materia.
4. ELECTIVA      La materia ya no existe (o era de libre elección): llena un cupo
                 de libre elección con créditos <= a los de la materia vista
                 (no se regalan créditos). Se elige el cupo que menos créditos
                 desperdicia.
5. REVISIÓN      No hay cupo que cumpla los créditos -> se abre un ticket para
                 que una persona decida.

Detalles:
- Si una materia se cursó varias veces se toma el mejor intento aprobado.
- Las materias que se están cursando no cuentan (se muestran aparte), salvo que
  se pida una proyección con `incluir_cursando=True`.
- Las materias de los pasos 3-5 se procesan de mayor a menor número de créditos,
  para que las grandes tengan prioridad sobre los cupos grandes.

Este módulo es puro: no lee archivos ni crea tickets; solo decide.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from app.domain.entities import (
    Equivalencia,
    EstadoMateria,
    Estudiante,
    Homologacion,
    Malla,
    Materia,
    MateriaCatalogo,
    MateriaVista,
    ResultadoTransicion,
    TipoHomologacion,
)


class MotorTransicion:
    def evaluar(
        self,
        estudiante: Estudiante,
        malla: Malla,
        equivalencias: list[Equivalencia] | None = None,
        catalogo: list[MateriaCatalogo] | None = None,
        incluir_cursando: bool = False,
    ) -> ResultadoTransicion:
        """Calcula cómo queda el estudiante en `malla`."""
        aprobadas, no_aprobadas, cursando = separar_historial(estudiante.materias_vistas)
        if incluir_cursando:
            aprobadas += [replace(v, estado=EstadoMateria.APROBADA) for v in cursando]
            cursando = []

        contexto = _Contexto(malla, equivalencias or [], catalogo or [], aprobadas)
        sin_ubicar: list[MateriaVista] = []

        # 1-2. Directas y equivalencias primero: una materia que sí existe en la
        # malla nueva nunca debe gastar un cupo de optativa o electiva.
        for vista in aprobadas:
            if not contexto.homologar_directa(vista):
                sin_ubicar.append(vista)
        sin_ubicar = [v for v in sin_ubicar if not contexto.homologar_equivalencia(v)]

        # 3-5. Optativas del catálogo, luego cupos de libre elección, luego revisión.
        for vista in sorted(sin_ubicar, key=lambda v: v.creditos, reverse=True):
            contexto.homologar_optativa(vista)
        restantes = [v for v in sin_ubicar if v.codigo not in contexto.ubicadas]
        for vista in sorted(restantes, key=lambda v: v.creditos, reverse=True):
            if not contexto.homologar_electiva(vista):
                contexto.enviar_a_revision(vista)

        pendientes = [m for m in malla.materias if m.codigo not in contexto.cubiertas]
        return ResultadoTransicion(
            estudiante=estudiante,
            malla_destino=malla,
            requiere_transicion=estudiante.malla_version != malla.version,
            homologaciones=contexto.homologaciones,
            materias_pendientes=sorted(pendientes, key=lambda m: (m.semestre, m.tipo.value, m.codigo)),
            materias_no_aprobadas=no_aprobadas,
            materias_cursando=cursando,
        )


# ---------------------------------------------------------------------------
# Historial
# ---------------------------------------------------------------------------
def separar_historial(
    vistas: list[MateriaVista],
) -> tuple[list[MateriaVista], list[MateriaVista], list[MateriaVista]]:
    """Devuelve (aprobadas, no_aprobadas, cursando) con un solo registro por materia.

    - Si la aprobó alguna vez: cuenta el intento aprobado con mejor nota.
    - Si no la ha aprobado pero la está cursando: queda en "cursando".
    - Si solo la reprobó: queda en "no aprobadas" (con su mejor nota).
    - Las canceladas no cuentan para nada.
    """
    intentos: dict[str, list[MateriaVista]] = defaultdict(list)
    for vista in vistas:
        if vista.estado is not EstadoMateria.CANCELADA:
            intentos[vista.codigo].append(vista)

    def mejor(lista: list[MateriaVista]) -> MateriaVista:
        return max(lista, key=lambda v: -1 if v.nota is None else v.nota)

    aprobadas, no_aprobadas, cursando = [], [], []
    for lista in intentos.values():
        ok = [v for v in lista if v.estado is EstadoMateria.APROBADA]
        en_curso = [v for v in lista if v.estado is EstadoMateria.CURSANDO]
        if ok:
            aprobadas.append(mejor(ok))
        elif en_curso:
            cursando.append(en_curso[-1])
        else:
            no_aprobadas.append(mejor(lista))
    return aprobadas, no_aprobadas, cursando


# ---------------------------------------------------------------------------
# Estado de una evaluación
# ---------------------------------------------------------------------------
class _Contexto:
    """Lleva la cuenta de qué cupos/materias de la malla destino ya están ocupados."""

    def __init__(
        self,
        malla: Malla,
        equivalencias: list[Equivalencia],
        catalogo: list[MateriaCatalogo],
        aprobadas: list[MateriaVista],
    ) -> None:
        self.malla = malla
        self.homologaciones: list[Homologacion] = []
        self.cubiertas: set[str] = set()      # códigos de la malla destino ya ocupados
        self.ubicadas: set[str] = set()       # códigos de materias vistas ya resueltas

        self._equivalencia_de = {e.codigo_anterior: e for e in equivalencias}
        self._fusion: dict[str, list[Equivalencia]] = defaultdict(list)
        for e in equivalencias:
            self._fusion[e.codigo_nuevo].append(e)
        self._grupos_de: dict[str, set[str]] = defaultdict(set)
        for c in catalogo:
            self._grupos_de[c.codigo].add(c.grupo)
        self._aprobadas = {v.codigo: v for v in aprobadas}

    def _registrar(self, vista: MateriaVista, tipo: TipoHomologacion, destino: Materia | None, obs: str) -> None:
        self.homologaciones.append(Homologacion(vista, tipo, destino, obs))
        self.ubicadas.add(vista.codigo)
        if destino:
            self.cubiertas.add(destino.codigo)

    # -- 1. directa -------------------------------------------------------------
    def homologar_directa(self, vista: MateriaVista) -> bool:
        destino = self.malla.buscar(vista.codigo)
        if destino is None or destino.codigo in self.cubiertas:
            return False
        obs = "La materia se mantiene en la malla vigente."
        if destino.creditos != vista.creditos:
            obs = (
                f"Se mantiene con el mismo código; en la malla {self.malla.version} vale "
                f"{destino.creditos} créditos (la vio con {vista.creditos})."
            )
        self._registrar(vista, TipoHomologacion.DIRECTA, destino, obs)
        return True

    # -- 2. equivalencia / fusión -----------------------------------------------
    def homologar_equivalencia(self, vista: MateriaVista) -> bool:
        if vista.codigo in self.ubicadas:
            return True                       # ya resuelta como parte de una fusión
        equivalencia = self._equivalencia_de.get(vista.codigo)
        destino = self.malla.buscar(equivalencia.codigo_nuevo) if equivalencia else None
        if destino is None or destino.codigo in self.cubiertas:
            return False

        partes = self._fusion[destino.codigo]
        nota_propuesta = " (equivalencia propuesta, pendiente de aval)" if equivalencia.estado == "propuesta" else ""

        if len(partes) == 1:
            self._registrar(
                vista, TipoHomologacion.EQUIVALENCIA, destino,
                f"Equivale a '{destino.nombre}' ({destino.codigo}){nota_propuesta}.",
            )
            return True

        faltantes = [p.codigo_anterior for p in partes if p.codigo_anterior not in self._aprobadas]
        if faltantes:
            self._registrar(
                vista, TipoHomologacion.REQUIERE_REVISION, None,
                f"'{vista.nombre}' se fusionó en '{destino.nombre}' ({destino.codigo}), que también "
                f"exige aprobar: {', '.join(faltantes)}. Fusión incompleta: requiere revisión.",
            )
            return True

        nombres = " + ".join(self._aprobadas[p.codigo_anterior].nombre for p in partes)
        for parte in partes:
            self._registrar(
                self._aprobadas[parte.codigo_anterior], TipoHomologacion.EQUIVALENCIA, destino,
                f"Fusión: {nombres} -> '{destino.nombre}' ({destino.codigo}){nota_propuesta}.",
            )
        return True

    # -- 3. optativa del catálogo ---------------------------------------------
    def homologar_optativa(self, vista: MateriaVista) -> bool:
        grupos = self._grupos_de.get(vista.codigo)
        if not grupos:
            return False
        candidatos = [
            m for m in self.malla.materias
            if m.es_cupo and m.grupo in grupos and m.codigo not in self.cubiertas
            and m.creditos <= vista.creditos
        ]
        if not candidatos:
            return False
        cupo = _menor_desperdicio(candidatos)
        self._registrar(
            vista, TipoHomologacion.OPTATIVA, cupo,
            f"Está en el catálogo de optativas; se reconoce como '{cupo.nombre}' ({cupo.creditos} créditos).",
        )
        return True

    # -- 4. cupo de libre elección ----------------------------------------------
    def homologar_electiva(self, vista: MateriaVista) -> bool:
        candidatos = [
            e for e in self.malla.electivas
            if e.codigo not in self.cubiertas and e.creditos <= vista.creditos
        ]
        if not candidatos:
            return False
        cupo = _menor_desperdicio(candidatos)
        if "libre" in vista.tipologia:
            motivo = f"Materia de libre elección; ocupa '{cupo.nombre}' ({cupo.creditos} créditos)."
        else:
            motivo = (
                f"'{vista.nombre}' no existe en la malla {self.malla.version}; se reconoce como "
                f"'{cupo.nombre}' ({cupo.creditos} créditos)."
            )
        self._registrar(vista, TipoHomologacion.REEMPLAZO_ELECTIVA, cupo, motivo)
        return True

    # -- 5. revisión ------------------------------------------------------------
    def enviar_a_revision(self, vista: MateriaVista) -> None:
        electivas = self.malla.electivas
        libres = [e for e in electivas if e.codigo not in self.cubiertas]
        if not electivas:
            causa = f"la malla {self.malla.version} no tiene cupos de libre elección"
        elif not libres:
            causa = "todos los cupos de libre elección ya están ocupados"
        else:
            causa = (
                f"los cupos de libre elección libres piden {min(e.creditos for e in libres)} créditos o más "
                f"y la materia tiene {vista.creditos}"
            )
        self._registrar(
            vista, TipoHomologacion.REQUIERE_REVISION, None,
            f"'{vista.nombre}' no tiene lugar en la malla {self.malla.version}: {causa}. Requiere revisión.",
        )


def _menor_desperdicio(cupos: list[Materia]) -> Materia:
    """El cupo con más créditos (menos desperdicio); a igualdad, el de semestre más bajo."""
    return min(cupos, key=lambda c: (-c.creditos, c.semestre, c.codigo))
