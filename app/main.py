from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.boxbrain import boxbrain_status
from app.commands import parse_command
from app.config import get_settings
from app.models import CommandRequest, HostDetectRequest, ProjectCreate, TaskApproval
from app.network import detect_host, normalize_domain
from app.store import Store

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def create_app(database_path: str | None = None) -> FastAPI:
    settings = get_settings()
    store = Store(database_path or settings.database_path)
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.store = store

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "service": "arkmatx-deploy",
            "environment": settings.environment,
            "network_probes": settings.allow_network_probes,
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
