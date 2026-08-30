from pathlib import Path


SOURCE = Path("app/image_studio_ui.py").read_text(encoding="utf-8")


def test_final_polling_state_is_declared():
    declaration = SOURCE.split("const el=", 1)[0]
    assert "finalPollJobId=null" in declaration
    assert "finalPollTimer=null" in declaration


def test_final_polling_function_uses_declared_state():
    assert "function startFinalPolling" in SOURCE
    assert "finalPollJobId" in SOURCE
