"""Raíz de composición: el único lugar que conoce TODAS las piezas concretas.

Aquí se decide, según la configuración, qué implementación usar para cada
puerto (Excel local o Drive, JWT, bcrypt, JSON...) y se construyen los casos de
uso ya conectados. El resto del código solo recibe lo que necesita.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.application.use_cases.auditoria import Auditor, ListarAuditoria
from app.application.use_cases.autenticacion import IniciarSesion, ValidarToken
from app.application.use_cases.estudiantes import (
    ConsultarMalla,
    ConsultarMiAvance,
    ListarEstudiantes,
    ValidarMallaEstudiante,
)
from app.application.use_cases.gestion_estudiantes import GestionEstudiantes
from app.application.use_cases.gestion_usuarios import GestionUsuarios
from app.application.use_cases.importacion import ImportarEstudiantes
from app.application.use_cases.tickets import CerrarTicket, ListarTickets
from app.domain.services.motor_transicion import MotorTransicion
from app.infrastructure.config import Settings
from app.infrastructure.data_sources.fuentes import (
    FuenteConCache,
    FuenteExcel,
    FuenteGoogleDrive,
    FuenteLocal,
)
from app.infrastructure.importacion.lector_importacion import ExcelLectorImportacion
from app.infrastructure.importacion.plantilla import generar_plantilla
from app.infrastructure.repositories.excel_academico import ExcelRepositorioAcademico
from app.infrastructure.repositories.excel_usuarios import ExcelRepositorioUsuarios
from app.infrastructure.repositories.json_auditoria import JsonlRepositorioAuditoria
from app.infrastructure.repositories.json_tickets import JsonRepositorioTickets
from app.infrastructure.security.bcrypt_hasher import BcryptHasher
from app.infrastructure.security.jwt_tokens import JwtServicioTokens


@dataclass(frozen=True)
class Contenedor:
    """Casos de uso listos para usar por la capa de presentación."""

    settings: Settings
    # sesión
    iniciar_sesion: IniciarSesion
    validar_token: ValidarToken
    # consulta
    listar_estudiantes: ListarEstudiantes
    consultar_malla: ConsultarMalla
    validar_malla: ValidarMallaEstudiante
    mi_avance: ConsultarMiAvance
    # administración
    gestion_estudiantes: GestionEstudiantes
    gestion_usuarios: GestionUsuarios
    importar_estudiantes: ImportarEstudiantes
    generar_plantilla: Callable[[], bytes]
    listar_tickets: ListarTickets
    cerrar_ticket: CerrarTicket
    listar_auditoria: ListarAuditoria


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
    repo_academico = ExcelRepositorioAcademico(fuente_academico, settings.nota_minima)
    repo_tickets = JsonRepositorioTickets(settings.tickets_path)
    repo_auditoria = JsonlRepositorioAuditoria(settings.auditoria_path)

    hasher = BcryptHasher()
    tokens = JwtServicioTokens(settings.jwt_secret, settings.jwt_algoritmo, settings.jwt_expiracion_minutos)

    # --- Dominio y servicios de aplicación ---
    motor = MotorTransicion()
    auditor = Auditor(repo_auditoria)
    validar_malla = ValidarMallaEstudiante(repo_academico, repo_tickets, motor, auditor, settings.malla_vigente)
    gestion_estudiantes = GestionEstudiantes(repo_academico, repo_usuarios, hasher, auditor)
    lector_importacion = ExcelLectorImportacion(settings.nota_minima)

    # --- Casos de uso ---
    return Contenedor(
        settings=settings,
        iniciar_sesion=IniciarSesion(repo_usuarios, hasher, tokens, auditor),
        validar_token=ValidarToken(tokens),
        listar_estudiantes=ListarEstudiantes(repo_academico),
        consultar_malla=ConsultarMalla(repo_academico),
        validar_malla=validar_malla,
        mi_avance=ConsultarMiAvance(validar_malla),
        gestion_estudiantes=gestion_estudiantes,
        gestion_usuarios=GestionUsuarios(repo_usuarios, repo_academico, hasher, auditor),
        importar_estudiantes=ImportarEstudiantes(
            repo_academico, repo_usuarios, hasher, auditor, lector_importacion, gestion_estudiantes
        ),
        generar_plantilla=generar_plantilla,
        listar_tickets=ListarTickets(repo_tickets),
        cerrar_ticket=CerrarTicket(repo_tickets, auditor),
        listar_auditoria=ListarAuditoria(repo_auditoria),
    )
