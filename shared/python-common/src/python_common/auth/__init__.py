from dataclasses import dataclass


@dataclass(slots=True)
class RequestContext:
    tenant_id: str = "default"
    user_id: str = "anonymous"
    roles: tuple[str, ...] = ()

