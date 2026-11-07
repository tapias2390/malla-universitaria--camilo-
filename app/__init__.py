"""Sistema de transición de mallas curriculares.

Capas (de adentro hacia afuera; cada capa solo conoce a las internas):

    domain          -> entidades y reglas de negocio puras (sin librerías externas)
    application     -> casos de uso y puertos (interfaces) que necesitan
    infrastructure  -> implementaciones concretas: Excel, Google Drive, JWT, bcrypt
    presentation    -> API HTTP (FastAPI) y la página web
    bootstrap       -> raíz de composición: conecta todo según la configuración
"""
