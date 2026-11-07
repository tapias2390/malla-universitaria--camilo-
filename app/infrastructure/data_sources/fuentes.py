"""Fuentes de archivos Excel: local, Google Drive y un envoltorio con caché."""
from __future__ import annotations

import io
import logging
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
    def obtener_bytes(self) -> bytes: ...


# ---------------------------------------------------------------------------
# Local
# ---------------------------------------------------------------------------
class FuenteLocal:
    """Lee el .xlsx desde disco. Útil para desarrollo y pruebas."""

    def __init__(self, ruta: str | Path) -> None:
        self._ruta = Path(ruta)

    def obtener_bytes(self) -> bytes:
        if not self._ruta.exists():
            raise ErrorFuenteDatos(
                f"No existe el archivo '{self._ruta}'. "
                "Ejecuta 'python scripts/crear_datos_ejemplo.py' para generar datos de prueba."
            )
        return self._ruta.read_bytes()


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
    """Descarga el archivo desde Google Drive usando una cuenta de servicio.

    Por seguridad los archivos NO necesitan ser públicos: basta con compartirlos
    (solo lectura) con el correo de la cuenta de servicio. Funciona tanto con un
    .xlsx subido a Drive como con una Hoja de cálculo de Google (se exporta a .xlsx).
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, link_o_id: str, ruta_credenciales: str | Path) -> None:
        self._file_id = extraer_id_drive(link_o_id)
        self._ruta_credenciales = Path(ruta_credenciales)
        self._servicio = None  # se crea la primera vez que se usa

    def _cliente(self):
        if self._servicio is None:
            # Importación diferida: el modo local no necesita estas librerías.
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            if not self._ruta_credenciales.exists():
                raise ErrorFuenteDatos(
                    f"No se encontró el archivo de credenciales '{self._ruta_credenciales}'."
                )
            credenciales = service_account.Credentials.from_service_account_file(
                str(self._ruta_credenciales), scopes=self.SCOPES
            )
            self._servicio = build("drive", "v3", credentials=credenciales, cache_discovery=False)
        return self._servicio

    def obtener_bytes(self) -> bytes:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

        try:
            archivos = self._cliente().files()
            meta = archivos.get(
                fileId=self._file_id, fields="name,mimeType", supportsAllDrives=True
            ).execute()

            if meta["mimeType"] == MIME_GOOGLE_SHEET:
                peticion = archivos.export_media(fileId=self._file_id, mimeType=MIME_XLSX)
            else:
                peticion = archivos.get_media(fileId=self._file_id, supportsAllDrives=True)

            buffer = io.BytesIO()
            descarga = MediaIoBaseDownload(buffer, peticion)
            terminado = False
            while not terminado:
                _, terminado = descarga.next_chunk()
            log.info("Descargado de Drive: %s", meta["name"])
            return buffer.getvalue()
        except HttpError as exc:
            raise ErrorFuenteDatos(
                f"Error leyendo el archivo de Drive ({exc.status_code}). "
                "¿Está compartido con la cuenta de servicio?"
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

    def invalidar(self) -> None:
        with self._lock:
            self._contenido = None
