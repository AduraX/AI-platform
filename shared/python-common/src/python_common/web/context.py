import uuid

from fastapi import Request

from python_common.schemas.auth import RequestContext

TENANT_ID_HEADER = "x-tenant-id"
USER_ID_HEADER = "x-user-id"
ROLES_HEADER = "x-roles"
REQUEST_ID_HEADER = "x-request-id"


def ensure_request_id(request_id: str | None) -> str:
    if request_id and request_id.strip():
        return request_id.strip()
    return str(uuid.uuid4())


def request_context_from_headers(request: Request) -> RequestContext:
    roles_header = request.headers.get(ROLES_HEADER, "")
    roles = [role.strip() for role in roles_header.split(",") if role.strip()]

    return RequestContext(
        tenant_id=request.headers.get(TENANT_ID_HEADER, "default"),
        user_id=request.headers.get(USER_ID_HEADER, "anonymous"),
        roles=roles,
        request_id=ensure_request_id(request.headers.get(REQUEST_ID_HEADER)),
    )


def request_context_to_headers(context: RequestContext) -> dict[str, str]:
    return {
        TENANT_ID_HEADER: context.tenant_id,
        USER_ID_HEADER: context.user_id,
        ROLES_HEADER: ",".join(context.roles),
        REQUEST_ID_HEADER: context.request_id,
    }
