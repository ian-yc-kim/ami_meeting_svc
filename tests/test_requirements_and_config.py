from pathlib import Path


def test_pyproject_contains_openai_and_tenacity():
    """Ensure pyproject.toml lists openai and tenacity dependencies."""
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "openai" in content, "pyproject.toml must contain 'openai'"
    assert "tenacity" in content, "pyproject.toml must contain 'tenacity'"


def test_config_contains_openai_env():
    """Ensure config.py exposes OPENAI_API_KEY variable."""
    content = Path("src/ami_meeting_svc/config.py").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in content, "config.py must contain 'OPENAI_API_KEY'"
