import pathlib


def test_api_md_contains_auth_endpoints():
    p = pathlib.Path("API.md")
    assert p.exists(), "API.md must exist"
    txt = p.read_text(encoding="utf8")
    assert "/auth/login" in txt, "API.md should document /auth/login"
    assert "/auth/logout" in txt, "API.md should document /auth/logout"


def test_readme_contains_setup_commands():
    p = pathlib.Path("README.md")
    assert p.exists(), "README.md must exist"
    txt = p.read_text(encoding="utf8")
    # Ensure README provides at least one of the common setup/run/test commands
    assert any(cmd in txt for cmd in ["make build", "make run", "make setup", "make unittest"]), \
        "README.md should include setup or run instructions (make targets)"


def test_readme_contains_openai_env_vars():
    p = pathlib.Path("README.md")
    assert p.exists(), "README.md must exist"
    txt = p.read_text(encoding="utf8")
    assert "OPENAI_API_KEY" in txt, "README.md should document OPENAI_API_KEY"
    assert "OPENAI_MODEL_NAME" in txt, "README.md should document OPENAI_MODEL_NAME"


def test_api_md_contains_meeting_endpoints_and_validation_rule():
    p = pathlib.Path("API.md")
    assert p.exists(), "API.md must exist"
    txt = p.read_text(encoding="utf8")
    assert "/meetings/" in txt, "API.md should document /meetings/ endpoint"
    assert "/meetings/{meeting_id}" in txt, "API.md should document meeting detail path"
    assert "at least 50" in txt, "API.md should document notes validation (at least 50)"
    assert "notes" in txt, "API.md should reference notes validation"
