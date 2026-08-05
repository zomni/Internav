from os import getenv

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, Response

router = APIRouter()


@router.get("/apk")
def download_apk() -> Response:
    path = getenv("APK_PATH", "/apk/capture-app-debug.apk")
    return FileResponse(path, filename="capture-app-debug.apk", media_type="application/vnd.android.package-archive")


@router.get("/api/v1/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
