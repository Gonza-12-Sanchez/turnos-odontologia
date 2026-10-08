"""Excepciones de negocio (mapean a respuestas HTTP en C-03+)."""


class BusinessError(Exception):
    """Error de regla de negocio con código HTTP asociado."""

    status_code: int = 422

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
