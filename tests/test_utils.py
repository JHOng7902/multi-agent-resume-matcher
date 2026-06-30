from utils import clean_text, resolve_api_key, resolve_model, validate_required_inputs


def test_clean_text_strips_and_collapses_excessive_whitespace():
    raw_text = "  Resume   text\n\n\nwith\t\tmany    spaces  "

    assert clean_text(raw_text) == "Resume text with many spaces"


def test_validate_required_inputs_rejects_empty_resume_and_job_description():
    errors = validate_required_inputs("   ", "\n")

    assert "Resume text is required." in errors
    assert "Job description text is required." in errors


def test_validate_required_inputs_accepts_present_values():
    errors = validate_required_inputs("Python and SQL experience", "Software tester role")

    assert errors == []


def test_resolve_api_key_uses_environment_only(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")

    assert resolve_api_key() == "env-key"


def test_resolve_api_key_returns_none_when_missing(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    assert resolve_api_key() is None


def test_resolve_model_uses_environment_value(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    assert resolve_model() == "deepseek-v4-pro"


def test_resolve_model_defaults_to_flash_when_missing(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    assert resolve_model() == "deepseek-v4-flash"
