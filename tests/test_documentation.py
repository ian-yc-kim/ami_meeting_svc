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
