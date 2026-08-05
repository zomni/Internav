from typing import Any


def success(
    data: Any = None, message: str = "", metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
        "errors": [],
        "metadata": metadata or {},
    }


def failure(
    code: str, message: str, details: Any = None, trace_id: str | None = None
) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": None,
        "errors": [{"code": code, "message": message, "details": details}],
        "metadata": {"trace_id": trace_id} if trace_id else {},
    }
