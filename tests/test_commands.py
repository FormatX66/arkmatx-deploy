from app.commands import parse_command


PROJECTS = [{"id": "1", "name": "Demo Website"}]


def test_preview_is_safe():
    result = parse_command("preview Demo Website", PROJECTS)
    assert result["ok"] is True
    assert result["action"] == "preview"
    assert result["requires_confirmation"] is False


def test_deploy_requires_confirmation():
    result = parse_command("ship Demo Website", PROJECTS)
    assert result["action"] == "deploy"
    assert result["requires_confirmation"] is True
    assert result["confirmation_phrase"] == "SHIP"


def test_unknown_command_is_rejected():
    assert parse_command("dance around", PROJECTS)["ok"] is False
