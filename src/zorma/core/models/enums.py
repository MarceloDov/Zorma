from enum import StrEnum


class TipoCondicion(StrEnum):
    EXTENSION = "extension"
    TAMANIO = "size"
    FECHA = "date"
    NOMBRE = "name"


class TipoAccion(StrEnum):
    MOVER = "move"
    COPIAR = "copy"
    RENOMBRAR = "rename"


class TipoEvento(StrEnum):
    CREADO = "created"
    MODIFICADO = "modified"
    MOVIDO = "moved"
    ELIMINADO = "deleted"


class EstadoClasificacion(StrEnum):
    EXITO = "success"
    ERROR = "error"
    OMITIDO = "skipped"
    CONFLICTO = "conflict"
    SIN_REGLA = "no_classified"
    FILTRADO = "filtered_out"


class UrgenciaNotificacion(StrEnum):
    BAJA = "low"
    NORMAL = "normal"
    CRITICA = "critical"
