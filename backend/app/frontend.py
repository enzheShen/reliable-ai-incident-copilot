from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):
    """Serve a React build while preserving 404s for backend-owned paths."""

    reserved_prefixes = ("api/", "health/", "metrics", "docs", "redoc", "openapi.json")

    async def get_response(self, path: str, scope: Scope) -> Response:
        if path.startswith(self.reserved_prefixes):
            return await super().get_response(path, scope)
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


def mount_frontend(application: FastAPI, directory: Path, *, required: bool) -> None:
    if not directory.is_dir():
        if required:
            raise RuntimeError(f"Production frontend build is missing: {directory}")
        return
    application.mount("/", SPAStaticFiles(directory=directory, html=True), name="frontend")
