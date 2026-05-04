class PlatformError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class UpstreamServiceError(PlatformError):
    def __init__(
        self,
        *,
        service: str,
        message: str,
        status_code: int = 502,
        details: dict[str, object] | None = None,
    ) -> None:
        merged_details = {"service": service}
        if details:
            merged_details.update(details)

        super().__init__(
            code="upstream_service_error",
            message=message,
            status_code=status_code,
            details=merged_details,
        )
