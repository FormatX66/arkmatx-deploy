import re


ACTIONS = {
    "deploy": ("deploy", True, "SHIP"),
    "ship": ("deploy", True, "SHIP"),
    "publish": ("deploy", True, "SHIP"),
    "rollback": ("rollback", True, "UNDO"),
    "undo": ("rollback", True, "UNDO"),
    "restore": ("rollback", True, "UNDO"),
    "preview": ("preview", False, ""),
    "test": ("test", False, ""),
    "check": ("test", False, ""),
    "status": ("status", False, ""),
    "backup": ("backup", False, ""),
    "clone": ("clone", True, "CLONE"),
}


def parse_command(text: str, projects: list[dict]) -> dict:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    action = None
    requires_confirmation = False
    confirmation_phrase = ""
    for word, definition in ACTIONS.items():
        if re.search(rf"\b{re.escape(word)}\b", normalized):
            action, requires_confirmation, confirmation_phrase = definition
            break
    if action is None:
        return {
            "ok": False,
            "message": "Try: preview Demo Website, test Demo Website, or ship Demo Website.",
        }

    project = next(
        (item for item in projects if item["name"].lower() in normalized),
        projects[0] if len(projects) == 1 else None,
    )
    if project is None:
        return {"ok": False, "message": "Name the project you want me to use."}

    return {
        "ok": True,
        "action": action,
        "project": project,
        "requires_confirmation": requires_confirmation,
        "confirmation_phrase": confirmation_phrase,
        "summary": f"{action.title()} {project['name']}",
    }
