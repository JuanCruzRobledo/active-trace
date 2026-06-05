import enum


class OrigenCalificacion(str, enum.Enum):
    IMPORTADO = "Importado"
    MANUAL = "Manual"


class EstadoEncuentro(str, enum.Enum):
    PROGRAMADO = "Programado"
    REALIZADO = "Realizado"
    CANCELADO = "Cancelado"


class EstadoGuardia(str, enum.Enum):
    PENDIENTE = "Pendiente"
    REALIZADA = "Realizada"
    CANCELADA = "Cancelada"


class DiaSemana(str, enum.Enum):
    LUNES = "Lunes"
    MARTES = "Martes"
    MIERCOLES = "Miércoles"
    JUEVES = "Jueves"
    VIERNES = "Viernes"
    SABADO = "Sábado"
    DOMINGO = "Domingo"
