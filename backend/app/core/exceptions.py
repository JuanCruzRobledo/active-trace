"""RESERVADO para C-02+: Handlers de error y excepciones estandarizadas.

Este módulo se completa en C-02 y siguientes con:
- ``AppException`` base y excepciones de dominio específicas.
- ``ExceptionHandler`` global de FastAPI.
- Códigos de error estandarizados.
"""


class BusinessError(Exception):
    """Excepción de dominio — violación de regla de negocio.

    Se traduce a HTTP 400 en el router correspondiente.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

