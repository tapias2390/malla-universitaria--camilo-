"""Repositorio académico sobre el Excel académico.

Hojas (los encabezados no distinguen mayúsculas ni tildes; la hoja LEEME del
archivo explica cada columna):

  estudiantes      codigo | nombre | documento | correo | malla_version | estado
  materias_vistas  codigo_estudiante | codigo_materia | nombre_materia | creditos |
                   nota | estado | tipologia | periodo
  mallas           version | semestre | codigo | nombre | creditos | tipo | grupo | observacion
  equivalencias    codigo_anterior | nombre_anterior | codigo_nuevo | nombre_nuevo |
                   estado | observacion                                (opcional)
  optativas        grupo | codigo | nombre                             (opcional)

Las mallas, equivalencias y optativas solo se leen (las mantiene la oficina
académica). Estudiantes e historial se leen y se escriben (CRUD del admin).
"""
from __future__ import annotations

import threading
from collections import defaultdict

from app.domain.entities import (
    Equivalencia,
    EstadoMateria,
    Estudiante,
    Malla,
    Materia,
    MateriaCatalogo,
    MateriaVista,
    TipoMateria,
)
from app.domain.exceptions import ErrorFuenteDatos
from app.infrastructure.data_sources.editor_excel import EditorExcel, HojaEditable
from app.infrastructure.data_sources.fuentes import FuenteExcel
from app.infrastructure.data_sources.lector_excel import (
    Fila,
    como_decimal_opcional,
    como_entero,
    como_texto,
    exigir_hoja,
    leer_libro,
    normalizar_encabezado,
)

COLUMNAS_ESTUDIANTES = {"codigo", "nombre", "documento", "malla_version"}
COLUMNAS_VISTAS = {"codigo_estudiante", "codigo_materia", "nombre_materia", "creditos", "nota"}
COLUMNAS_MALLAS = {"version", "codigo", "nombre", "creditos", "semestre", "tipo"}

# Orden de columnas al escribir (las que falten en el archivo se agregan al final).
ESCRITURA_ESTUDIANTES = ["codigo", "nombre", "documento", "correo", "malla_version", "estado"]
ESCRITURA_VISTAS = [
    "codigo_estudiante", "codigo_materia", "nombre_materia", "creditos",
    "nota", "estado", "tipologia", "periodo",
]

# Cómo se escribe el estado de una materia en el Excel -> estado del dominio.
SINONIMOS_ESTADO = {
    EstadoMateria.APROBADA: {"aprobada", "aprobado", "ap", "suf", "aprobada_(suf)", "hom", "homologada",
                             "convalidada", "validada"},
    EstadoMateria.REPROBADA: {"reprobada", "reprobado", "perdida", "rep"},
    EstadoMateria.CURSANDO: {"cursando", "en_curso", "inscrita", "inscrito"},
    EstadoMateria.CANCELADA: {"cancelada", "cancelado", "anulada"},
}

# Letra de tipología del reporte de la universidad -> nombre normalizado.
TIPOLOGIAS = {
    "b": "fund_obligatoria", "c": "disciplinar_obligatoria", "o": "fund_optativa",
    "t": "disciplinar_optativa", "l": "libre_eleccion", "e": "nivelacion", "p": "trabajo_de_grado",
}


class ExcelRepositorioAcademico:
    def __init__(self, fuente: FuenteExcel, nota_minima: float = 3.0) -> None:
        self._fuente = fuente
        self._editor = EditorExcel(fuente)
        self._nota_minima = nota_minima
        # El libro se parsea una sola vez por cada versión descargada del archivo.
        self._lock = threading.Lock()
        self._contenido_previo: bytes | None = None
        self._hojas: dict[str, list[Fila]] = {}

    # ------------------------------------------------------------- lectura base
    def _libro(self) -> dict[str, list[Fila]]:
        contenido = self._fuente.obtener_bytes()
        with self._lock:
            if contenido != self._contenido_previo:
                self._hojas = leer_libro(contenido)
                self._contenido_previo = contenido
            return self._hojas

    # ------------------------------------------------------------- estudiantes
    def listar_estudiantes(self) -> list[Estudiante]:
        filas = exigir_hoja(self._libro(), "estudiantes", COLUMNAS_ESTUDIANTES)
        return [self._a_estudiante(f) for f in filas if como_texto(f.get("codigo"))]

    def obtener_estudiante(self, codigo: str) -> Estudiante | None:
        libro = self._libro()
        filas = exigir_hoja(libro, "estudiantes", COLUMNAS_ESTUDIANTES)
        fila = next((f for f in filas if como_texto(f.get("codigo")) == codigo), None)
        if fila is None:
            return None

        estudiante = self._a_estudiante(fila)
        vistas = exigir_hoja(libro, "materias_vistas", COLUMNAS_VISTAS)
        estudiante.materias_vistas = [
            self._a_materia_vista(v) for v in vistas if como_texto(v.get("codigo_estudiante")) == codigo
        ]
        return estudiante

    @staticmethod
    def _a_estudiante(fila: Fila) -> Estudiante:
        return Estudiante(
            codigo=como_texto(fila.get("codigo")),
            nombre=como_texto(fila.get("nombre")),
            documento=como_texto(fila.get("documento")),
            malla_version=como_texto(fila.get("malla_version")),
            estado=como_texto(fila.get("estado")).lower() or "activo",
            correo=como_texto(fila.get("correo")),
        )

    def _a_materia_vista(self, fila: Fila) -> MateriaVista:
        nota = como_decimal_opcional(fila.get("nota"))
        return MateriaVista(
            codigo=como_texto(fila.get("codigo_materia")),
            nombre=como_texto(fila.get("nombre_materia")),
            creditos=como_entero(fila.get("creditos")),
            nota=nota,
            periodo=como_texto(fila.get("periodo")),
            estado=self._interpretar_estado(fila.get("estado"), nota),
            tipologia=interpretar_tipologia(fila.get("tipologia")),
        )

    def _interpretar_estado(self, valor: object, nota: float | None) -> EstadoMateria:
        return interpretar_estado(valor, nota, self._nota_minima)

    # ------------------------------------------------------------- escritura
    def guardar_estudiante(self, estudiante: Estudiante) -> None:
        with self._editor.editar() as libro:
            _escribir_estudiante(HojaEditable(libro, "estudiantes", ESCRITURA_ESTUDIANTES), estudiante)

    def guardar_lote(self, estudiantes: list[Estudiante], historiales: dict[str, list[MateriaVista]]) -> None:
        with self._editor.editar() as libro:
            hoja_estudiantes = HojaEditable(libro, "estudiantes", ESCRITURA_ESTUDIANTES)
            for estudiante in estudiantes:
                _escribir_estudiante(hoja_estudiantes, estudiante)
            hoja_vistas = HojaEditable(libro, "materias_vistas", ESCRITURA_VISTAS)
            codigos = set(historiales)
            hoja_vistas.eliminar_donde(lambda leer: como_texto(leer("codigo_estudiante")) in codigos)
            for codigo, materias in historiales.items():
                for m in materias:
                    hoja_vistas.agregar(_fila_vista(codigo, m))

    def eliminar_estudiante(self, codigo: str) -> None:
        with self._editor.editar() as libro:
            HojaEditable(libro, "estudiantes", ESCRITURA_ESTUDIANTES).eliminar_donde(
                lambda leer: como_texto(leer("codigo")) == codigo
            )
            HojaEditable(libro, "materias_vistas", ESCRITURA_VISTAS).eliminar_donde(
                lambda leer: como_texto(leer("codigo_estudiante")) == codigo
            )

    def guardar_historial(self, codigo: str, materias: list[MateriaVista]) -> None:
        with self._editor.editar() as libro:
            hoja = HojaEditable(libro, "materias_vistas", ESCRITURA_VISTAS)
            hoja.eliminar_donde(lambda leer: como_texto(leer("codigo_estudiante")) == codigo)
            for m in materias:
                hoja.agregar(_fila_vista(codigo, m))

    # ------------------------------------------------------------- mallas
    def _materias_por_version(self) -> dict[str, list[Materia]]:
        filas = exigir_hoja(self._libro(), "mallas", COLUMNAS_MALLAS)
        por_version: dict[str, list[Materia]] = defaultdict(list)
        for f in filas:
            if como_texto(f.get("codigo")):
                por_version[como_texto(f.get("version"))].append(self._a_materia(f))
        return por_version

    def versiones_malla(self) -> list[str]:
        return sorted(self._materias_por_version())

    def obtener_malla(self, version: str) -> Malla | None:
        materias = self._materias_por_version().get(version)
        return Malla(version=version, materias=materias) if materias else None

    @staticmethod
    def _a_materia(fila: Fila) -> Materia:
        tipo_texto = normalizar_encabezado(fila.get("tipo"))
        tipo_texto = {"libre_eleccion": "electiva", "libre": "electiva"}.get(tipo_texto, tipo_texto)
        try:
            tipo = TipoMateria(tipo_texto)
        except ValueError as exc:
            raise ErrorFuenteDatos(
                f"Tipo de materia inválido '{fila.get('tipo')}' en la hoja 'mallas' "
                "(use obligatoria, optativa, electiva o nivelacion)."
            ) from exc
        return Materia(
            codigo=como_texto(fila.get("codigo")),
            nombre=como_texto(fila.get("nombre")),
            creditos=como_entero(fila.get("creditos")),
            semestre=como_entero(fila.get("semestre")),
            tipo=tipo,
            grupo=normalizar_encabezado(fila.get("grupo")),
            observacion=como_texto(fila.get("observacion")),
        )

    # ------------------------------------------------------------- equivalencias / optativas
    def obtener_equivalencias(self) -> list[Equivalencia]:
        filas = self._libro().get("equivalencias", [])  # hoja opcional
        return [
            Equivalencia(
                codigo_anterior=como_texto(f.get("codigo_anterior")),
                codigo_nuevo=como_texto(f.get("codigo_nuevo")),
                estado=como_texto(f.get("estado")).lower() or "confirmada",
                observacion=como_texto(f.get("observacion")),
            )
            for f in filas
            if como_texto(f.get("codigo_anterior")) and como_texto(f.get("codigo_nuevo"))
        ]

    def obtener_catalogo_optativas(self) -> list[MateriaCatalogo]:
        filas = self._libro().get("optativas", [])  # hoja opcional
        return [
            MateriaCatalogo(
                grupo=normalizar_encabezado(f.get("grupo")),
                codigo=como_texto(f.get("codigo")),
                nombre=como_texto(f.get("nombre")),
            )
            for f in filas
            if como_texto(f.get("codigo")) and como_texto(f.get("grupo"))
        ]


def _escribir_estudiante(hoja: HojaEditable, estudiante: Estudiante) -> None:
    hoja.reemplazar_o_agregar(
        {"codigo": estudiante.codigo},
        {
            "nombre": estudiante.nombre,
            "documento": estudiante.documento,
            "correo": estudiante.correo,
            "malla_version": estudiante.malla_version,
            "estado": estudiante.estado,
        },
    )


def _fila_vista(codigo: str, m: MateriaVista) -> dict[str, object]:
    return {
        "codigo_estudiante": codigo,
        "codigo_materia": m.codigo,
        "nombre_materia": m.nombre,
        "creditos": m.creditos,
        "nota": m.nota,
        "estado": m.estado.value,
        "tipologia": m.tipologia,
        "periodo": m.periodo,
    }


def interpretar_estado(valor: object, nota: float | None, nota_minima: float) -> EstadoMateria:
    """'Aprobada (SUF)', 'reprobada', 'cursando'... -> estado. Vacío: se deduce de la nota."""
    texto = normalizar_encabezado(valor)
    for estado, sinonimos in SINONIMOS_ESTADO.items():
        if texto in sinonimos or texto.startswith(estado.value):
            return estado
    if texto:
        raise ErrorFuenteDatos(
            f"Estado de materia desconocido '{valor}' (use aprobada, reprobada, cursando o cancelada)."
        )
    # Sin estado escrito: se deduce de la nota; sin nota se asume que la está cursando.
    if nota is None:
        return EstadoMateria.CURSANDO
    return EstadoMateria.APROBADA if nota >= nota_minima else EstadoMateria.REPROBADA


def interpretar_tipologia(valor: object) -> str:
    """'Fund. Obligatoria', 'B' o 'fund_obligatoria' -> 'fund_obligatoria'."""
    texto = normalizar_encabezado(valor).replace(".", "")
    return TIPOLOGIAS.get(texto, texto)
