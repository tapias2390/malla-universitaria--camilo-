"""Errores de negocio.

La capa de presentación los traduce a códigos HTTP; el dominio no sabe nada de HTTP.
"""


class ErrorDominio(Exception):
    """Base de todos los errores de negocio."""


class CredencialesInvalidas(ErrorDominio):
    """Usuario inexistente, inactivo o contraseña incorrecta.

    Se usa el mismo error para todos los casos a propósito: así no se revela
    si un usuario existe o no.
    """


class TokenInvalido(ErrorDominio):
    """El token JWT está vencido, alterado o mal formado."""


class AccesoDenegado(ErrorDominio):
    """El usuario está autenticado pero su rol no permite la operación."""


class EstudianteNoEncontrado(ErrorDominio):
    pass


class MallaNoEncontrada(ErrorDominio):
    pass


class TicketNoEncontrado(ErrorDominio):
    pass


class UsuarioNoEncontrado(ErrorDominio):
    pass


class DatosInvalidos(ErrorDominio):
    """Los datos enviados no cumplen una regla (p. ej. malla inexistente, créditos negativos)."""


class RegistroDuplicado(ErrorDominio):
    """Ya existe un registro con esa clave (código de estudiante, usuario...)."""


class ErrorFuenteDatos(ErrorDominio):
    """No se pudo leer el origen de datos (Drive caído, hoja faltante, columnas mal nombradas...)."""
