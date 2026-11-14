"""Fuentes de archivos Excel: local, Google Drive y un envoltorio con caché.

Todas leen y escriben el archivo completo como bytes; interpretar las hojas es
trabajo de `lector_excel` (lectura) y `editor_excel` (escritura).
"""
from __future__ import annotations

import io
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Protocol

from app.domain.exceptions import ErrorFuenteDatos

log = logging.getLogger(__name__)

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"


class FuenteExcel(Protocol):
    def obtener_bytes(self) -> bytes:
        """Contenido del archivo (puede venir de una caché)."""
        ...

    def obtener_bytes_frescos(self) -> bytes:
        """Contenido actual del origen, sin caché. Se usa antes de modificar el archivo."""
        ...

    def guardar_bytes(self, contenido: bytes) -> None:
        """Reemplaza el archivo con `contenido`."""
        ...


# ---------------------------------------------------------------------------
# Local
# ---------------------------------------------------------------------------
class FuenteLocal:
    """Lee y escribe el .xlsx en disco. Útil para desarrollo y pruebas."""

    def __init__(self, ruta: str | Path) -> None:
        self._ruta = Path(ruta)

    def obtener_bytes(self) -> bytes:
        if not self._ruta.exists():
            raise ErrorFuenteDatos(
                f"No existe el archivo '{self._ruta}'. "
                "Ejecute 'python scripts/crear_datos_ejemplo.py' para generar los datos de prueba."
            )
        return self._ruta.read_bytes()

    def obtener_bytes_frescos(self) -> bytes:
        return self.obtener_bytes()

    def guardar_bytes(self, contenido: bytes) -> None:
        # Escritura atómica: temporal + reemplazo, para no dejar el Excel a medias.
        temporal = self._ruta.with_suffix(".tmp")
        temporal.write_bytes(contenido)
        try:
            os.replace(temporal, self._ruta)
        except PermissionError as exc:
            temporal.unlink(missing_ok=True)
            raise ErrorFuenteDatos(
                f"No se pudo guardar '{self._ruta.name}'. ¿Está abierto en Excel? Ciérrelo e intente de nuevo."
            ) from exc


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------
def extraer_id_drive(link_o_id: str) -> str:
    """Saca el ID del archivo de cualquier formato de link de Drive / Sheets.

    Acepta, por ejemplo:
      https://docs.google.com/spreadsheets/d/<ID>/edit#gid=0
      https://drive.google.com/file/d/<ID>/view
      https://drive.google.com/open?id=<ID>
      <ID>
    """
    link_o_id = link_o_id.strip()
    for patron in (r"/d/([a-zA-Z0-9_-]{10,})", r"[?&]id=([a-zA-Z0-9_-]{10,})"):
        coincidencia = re.search(patron, link_o_id)
        if coincidencia:
            return coincidencia.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", link_o_id):
        return link_o_id
    raise ErrorFuenteDatos(f"No se reconoce el link de Drive: '{link_o_id}'.")


class FuenteGoogleDrive:
    """Lee y escribe el archivo en Google Drive usando una cuenta de servicio.

    Por seguridad los archivos NO necesitan ser públicos: basta con compartirlos
    con el correo de la cuenta de servicio. Funciona tanto con un .xlsx subido a
    Drive como con una Hoja de cálculo de Google (se exporta/importa como .xlsx).

    - Leer usa un permiso de SOLO LECTURA.
    - Guardar (registro de estudiantes y usuarios) pide permiso de escritura solo
      en ese momento; para eso el archivo debe compartirse como "Editor".
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    SCOPES_ESCRITURA = ["https://www.googleapis.com/auth/drive"]
    REINTENTOS = 3

    def __init__(self, link_o_id: str, ruta_credenciales: str | Path) -> None:
        self._file_id = extraer_id_drive(link_o_id)
        self._ruta_credenciales = Path(ruta_credenciales)
        self._credenciales = None            # se cargan la primera vez que se usan
        self._credenciales_escritura = None

    def _cargar_credenciales(self, scopes: list[str]):
        from google.oauth2 import service_account

        if not self._ruta_credenciales.exists():
            raise ErrorFuenteDatos(f"No se encontró el archivo de credenciales '{self._ruta_credenciales}'.")
        return service_account.Credentials.from_service_account_file(str(self._ruta_credenciales), scopes=scopes)

    def _cliente(self, escritura: bool = False):
        """Crea un cliente NUEVO en cada operación.

        El transporte HTTP de la librería de Google (httplib2) no es seguro entre
        hilos y FastAPI atiende las peticiones en hilos distintos; compartir un
        único cliente provocaba errores intermitentes. Las credenciales sí se
        reutilizan (son seguras y guardan el token de acceso).
        """
        # Importación diferida: el modo local no necesita estas librerías.
        from googleapiclient.discovery import build

        if escritura:
            if self._credenciales_escritura is None:
                self._credenciales_escritura = self._cargar_credenciales(self.SCOPES_ESCRITURA)
            credenciales = self._credenciales_escritura
        else:
            if self._credenciales is None:
                self._credenciales = self._cargar_credenciales(self.SCOPES)
            credenciales = self._credenciales
        return build("drive", "v3", credentials=credenciales, cache_discovery=False)

    def obtener_bytes(self) -> bytes:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

        try:
            archivos = self._cliente().files()
            meta = archivos.get(
                fileId=self._file_id, fields="name,mimeType", supportsAllDrives=True
            ).execute(num_retries=self.REINTENTOS)

            if meta["mimeType"] == MIME_GOOGLE_SHEET:
                peticion = archivos.export_media(fileId=self._file_id, mimeType=MIME_XLSX)
            else:
                peticion = archivos.get_media(fileId=self._file_id, supportsAllDrives=True)

            buffer = io.BytesIO()
            descarga = MediaIoBaseDownload(buffer, peticion)
            terminado = False
            while not terminado:
                _, terminado = descarga.next_chunk(num_retries=self.REINTENTOS)
            log.info("Descargado de Drive: %s", meta["name"])
            return buffer.getvalue()
        except HttpError as exc:
            raise ErrorFuenteDatos(
                f"Error leyendo el archivo de Drive ({exc.status_code}). "
                "¿Está compartido con la cuenta de servicio?"
            ) from exc
        except ErrorFuenteDatos:
            raise
        except Exception as exc:  # red caída, SSL, tiempo agotado, credenciales dañadas...
            log.exception("Fallo de conexión con Google Drive")
            raise ErrorFuenteDatos(
                f"No se pudo conectar con Google Drive ({type(exc).__name__}). Intente de nuevo."
            ) from exc

    def obtener_bytes_frescos(self) -> bytes:
        return self.obtener_bytes()

    def guardar_bytes(self, contenido: bytes) -> None:
        """Sube el archivo modificado. Si es una Hoja de Google, Drive la convierte."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseUpload

        try:
            media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=MIME_XLSX, resumable=False)
            self._cliente(escritura=True).files().update(
                fileId=self._file_id, media_body=media, supportsAllDrives=True
            ).execute(num_retries=self.REINTENTOS)
            log.info("Archivo actualizado en Drive (%s)", self._file_id)
        except HttpError as exc:
            if exc.status_code in (401, 403, 404):
                raise ErrorFuenteDatos(
                    "No se pudo guardar en Drive: comparta el archivo con la cuenta de servicio "
                    "como 'Editor' (hoy solo puede leerlo)."
                ) from exc
            raise ErrorFuenteDatos(f"Error guardando en Drive ({exc.status_code}).") from exc
        except ErrorFuenteDatos:
            raise
        except Exception as exc:
            log.exception("Fallo de conexión con Google Drive al guardar")
            raise ErrorFuenteDatos(
                f"No se pudo guardar en Google Drive ({type(exc).__name__}). Intente de nuevo."
            ) from exc


# ---------------------------------------------------------------------------
# Caché
# ---------------------------------------------------------------------------
class FuenteConCache:
    """Guarda en memoria el último archivo descargado durante `ttl_segundos`.

    Evita descargar de Drive en cada petición. Si Drive falla y hay una copia
    previa, se sigue usando esa copia (y se registra una advertencia).
    """

    def __init__(self, fuente: FuenteExcel, ttl_segundos: int) -> None:
        self._fuente = fuente
        self._ttl = ttl_segundos
        self._contenido: bytes | None = None
        self._momento = 0.0
        self._lock = threading.Lock()

    def obtener_bytes(self) -> bytes:
        with self._lock:
            vigente = self._contenido is not None and (time.monotonic() - self._momento) < self._ttl
            if vigente:
                return self._contenido
            try:
                self._contenido = self._fuente.obtener_bytes()
                self._momento = time.monotonic()
            except ErrorFuenteDatos:
                if self._contenido is None:
                    raise
                log.warning("No se pudo refrescar la fuente; se usa la copia en caché.", exc_info=True)
            return self._contenido

    def obtener_bytes_frescos(self) -> bytes:
        """Ignora la caché: antes de modificar hay que partir de la versión real."""
        contenido = self._fuente.obtener_bytes_frescos()
        with self._lock:
            self._contenido, self._momento = contenido, time.monotonic()
        return contenido

    def guardar_bytes(self, contenido: bytes) -> None:
        self._fuente.guardar_bytes(contenido)
        with self._lock:
            # Lo recién guardado es la versión vigente: se sirve sin volver a descargar.
            self._contenido, self._momento = contenido, time.monotonic()

    def invalidar(self) -> None:
        with self._lock:
            self._contenido = None
