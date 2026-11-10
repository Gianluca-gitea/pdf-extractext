class InvalidPDFError(ValueError):
    pass


class ExtractServiceError(RuntimeError):
    pass


class ExtractServiceBusyError(ExtractServiceError):
    def __init__(self, retry_after: str) -> None:
        super().__init__("Servicio de extracción saturado.")
        self.retry_after = retry_after


class ExtractServiceUnavailableError(ExtractServiceError):
    pass


class ExtractServiceTimeoutError(ExtractServiceUnavailableError):
    pass


class InvalidStatusTransitionError(ValueError):
    pass
