"""Configuración leída desde variables de entorno / archivo .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- JWT ---
    jwt_secret: str = Field(..., description="Clave para firmar los tokens")
    jwt_algoritmo: str = "HS256"
    jwt_expiracion_minutos: int = 60

    # --- Fuente de datos ---
    fuente_datos: Literal["local", "drive"] = "local"
    usuarios_excel_path: str = "data/usuarios.xlsx"
    academico_excel_path: str = "data/academico.xlsx"
    usuarios_excel_link: str = ""
    academico_excel_link: str = ""
    google_credenciales: str = "credenciales/service_account.json"
    cache_segundos: int = 300

    # --- Reglas académicas ---
    malla_vigente: str = "2025"
    nota_minima: float = 3.0

    # --- Tickets ---
    tickets_path: str = "data/tickets.json"

    @field_validator("jwt_secret")
    @classmethod
    def _secreto_fuerte(cls, valor: str) -> str:
        if len(valor) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres.")
        return valor

    @model_validator(mode="after")
    def _links_si_es_drive(self) -> "Settings":
        # En modo drive, cada archivo con link se lee de Drive y el que no tenga
        # link se sigue leyendo en local (útil mientras se migra uno por uno).
        if self.fuente_datos == "drive" and not (self.usuarios_excel_link or self.academico_excel_link):
            raise ValueError(
                "Con FUENTE_DATOS=drive hay que definir USUARIOS_EXCEL_LINK y/o ACADEMICO_EXCEL_LINK."
            )
        return self


@lru_cache
def obtener_settings() -> Settings:
    return Settings()
