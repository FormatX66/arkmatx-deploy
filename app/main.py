from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from app.boxbrain import boxbrain_status
from app.commands import parse_command
from app.config import Settings, get_settings
from app.host_connection import HostConnectionError, SUPPORTED_PROTOCOLS, test_host_connection
from app.models import (
    CommandRequest,
    HostConnectionTestRequest,
    HostDetectRequest,
    ProjectCreate,
    TaskApproval,
)
from app.network import detect_host, normalize_domain
from app.rate_limit import SlidingWindowLimiter
from app.store import Store

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def create_app(
    database_path: str | None = None, settings_override: Settings | None = None
) -> FastAPI:
    settings = settings_override or get_settings()
    store = Store(database_path or settings.database_path)
    limiter = SlidingWindowLimiter(
        settings.connection_test_rate_limit, settings.connection_test_rate_window_seconds
    )
    app = FastAPI(title=settings.app_name, version="0.2.0")
    app.state.store = store
    app.state.connection_limiter = limiter

    @app.middleware("http")
    async def protect_sensitive_responses(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/hosts"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "service": "arkmatx-deploy",
            "environment": settings.environment,
            "network_probes": settings.allow_network_probes,
            "host_authentication_tests": settings.allow_network_probes,
            "supported_host_protocols": sorted(SUPPORTED_PROTOCOLS),
        }

    @app.get("/api/projects")
    def list_projects():
        return {"items": store.list_projects()}

    @app.post("/api/projects", status_code=201)
    def create_project(payload: ProjectCreate):
        return store.create_project(payload.name.strip(), payload.repository, payload.site_url)

    @app.get("/api/hosts")
    def list_hosts():
        return {"items": store.list_hosts()}

    @app.post("/api/hosts/detect")
    def detect(payload: HostDetectRequest):
        try:
            domain = normalize_domain(payload.domain)
            result = detect_host(domain, payload.protocol.lower(), payload.port, settings)
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result["username_received"] = bool(payload.username)
        result["password_received"] = payload.password is not None
        return result

    @app.post("/api/hosts/test")
    def test_connection(payload: HostConnectionTestRequest, request: Request, response: Response):
        client_key = request.client.host if request.client else "unknown"
        if not limiter.allow(client_key):
            raise HTTPException(
                status_code=429,
                detail="Too many connection tests. Wait a minute and try again.",
            )
        try:
            domain = normalize_domain(payload.domain)
            password = payload.password.get_secret_value()
            result = test_host_connection(
                domain,
                payload.protocol,
                payload.port,
                payload.username,
                password,
                settings,
            )
        except HostConnectionError as exc:
            status_code = 503 if exc.code == "network-tests-disabled" else 400
            raise HTTPException(
                status_code=status_code,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            password = None
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return result

    @app.post("/api/commands", status_code=201)
    def command(payload: CommandRequest):
        parsed = parse_command(payload.text, store.list_projects())
        if not parsed["ok"]:
            raise HTTPException(status_code=400, detail=parsed["message"])
        task = store.create_task(
            parsed["project"]["id"],
            parsed["action"],
            parsed["requires_confirmation"],
            parsed["confirmation_phrase"],
            {"summary": parsed["summary"], "source": "command-bar"},
        )
        return {"parsed": parsed, "task": task}

    @app.get("/api/tasks")
    def tasks():
        return {"items": store.list_tasks()}

    @app.post("/api/tasks/{task_id}/approve")
    def approve(task_id: str, payload: TaskApproval):
        task, result = store.approve_task(task_id, payload.confirmation)
        if result == "not-found":
            raise HTTPException(status_code=404, detail="Task not found")
        if result == "wrong-confirmation":
            raise HTTPException(status_code=400, detail="Confirmation phrase does not match")
        return {"result": result, "task": task}

    @app.get("/api/connectors")
    async def connectors():
        boxbrain = await boxbrain_status(settings)
        return {
            "items": [
                {"name": "BoxBrain", **boxbrain},
                {
                    "name": "Brain Connect",
                    "configured": False,
                    "status": "adapter-ready",
                    "capabilities": ["hosts", "machines", "apis", "files"],
                },
            ]
        }

    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
    return app


app = create_app()
