"""Raíz de composición: el único lugar que conoce TODAS las piezas concretas.

Aquí se decide, según la configuración, qué implementación usar para cada
puerto (Excel local o Drive, JWT, bcrypt, JSON...) y se construyen los casos de
uso ya conectados. El resto del código solo recibe lo que necesita.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases.autenticacion import IniciarSesion, ValidarToken
from app.application.use_cases.estudiantes import (
    ConsultarMalla,
    ListarEstudiantes,
    ValidarMallaEstudiante,
)
from app.application.use_cases.tickets import CerrarTicket, ListarTickets
from app.domain.services.motor_transicion import MotorTransicion
from app.infrastructure.config import Settings
from app.infrastructure.data_sources.fuentes import (
    FuenteConCache,
    FuenteExcel,
    FuenteGoogleDrive,
    FuenteLocal,
)
from app.infrastructure.repositories.excel_academico import ExcelRepositorioAcademico
from app.infrastructure.repositories.excel_usuarios import ExcelRepositorioUsuarios
from app.infrastructure.repositories.json_tickets import JsonRepositorioTickets
from app.infrastructure.security.bcrypt_hasher import BcryptHasher
from app.infrastructure.security.jwt_tokens import JwtServicioTokens


@dataclass(frozen=True)
class Contenedor:
    """Casos de uso listos para usar por la capa de presentación."""

    settings: Settings
    iniciar_sesion: IniciarSesion
    validar_token: ValidarToken
    listar_estudiantes: ListarEstudiantes
    consultar_malla: ConsultarMalla
    validar_malla: ValidarMallaEstudiante
    listar_tickets: ListarTickets
    cerrar_ticket: CerrarTicket


def _crear_fuente(settings: Settings, link: str, ruta_local: str) -> FuenteExcel:
    if settings.fuente_datos == "drive" and link:
        fuente: FuenteExcel = FuenteGoogleDrive(link, settings.google_credenciales)
        return FuenteConCache(fuente, settings.cache_segundos)
    # En local (o si ese archivo aún no tiene link) se lee el disco cada vez:
    # así los cambios en el Excel se ven al instante.
    return FuenteLocal(ruta_local)


def construir_contenedor(settings: Settings) -> Contenedor:
    # --- Infraestructura ---
    fuente_usuarios = _crear_fuente(settings, settings.usuarios_excel_link, settings.usuarios_excel_path)
    fuente_academico = _crear_fuente(settings, settings.academico_excel_link, settings.academico_excel_path)

    repo_usuarios = ExcelRepositorioUsuarios(fuente_usuarios)
    repo_academico = ExcelRepositorioAcademico(fuente_academico)
    repo_tickets = JsonRepositorioTickets(settings.tickets_path)

    hasher = BcryptHasher()
    tokens = JwtServicioTokens(
        settings.jwt_secret, settings.jwt_algoritmo, settings.jwt_expiracion_minutos
    )

    # --- Dominio ---
    motor = MotorTransicion(nota_minima=settings.nota_minima)

    # --- Casos de uso ---
    return Contenedor(
        settings=settings,
        iniciar_sesion=IniciarSesion(repo_usuarios, hasher, tokens),
        validar_token=ValidarToken(tokens),
        listar_estudiantes=ListarEstudiantes(repo_academico),
        consultar_malla=ConsultarMalla(repo_academico),
        validar_malla=ValidarMallaEstudiante(repo_academico, repo_tickets, motor, settings.malla_vigente),
        listar_tickets=ListarTickets(repo_tickets),
        cerrar_ticket=CerrarTicket(repo_tickets),
    )
