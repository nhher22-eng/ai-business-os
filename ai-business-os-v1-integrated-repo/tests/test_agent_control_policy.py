from app.services.agent_control import (
    evaluate_control_policy,
)


def test_agent_on_allows():
    decision = evaluate_control_policy(
        tenant_paused=False,
        desired_state="on",
    )
    assert decision.allowed is True
    assert decision.reason_code == "OK"


def test_agent_off_blocks():
    decision = evaluate_control_policy(
        tenant_paused=False,
        desired_state="off",
    )
    assert decision.allowed is False
    assert decision.reason_code == "AGENT_USER_OFF"


def test_agent_pause_blocks():
    decision = evaluate_control_policy(
        tenant_paused=False,
        desired_state="paused",
    )
    assert decision.allowed is False
    assert decision.reason_code == "AGENT_USER_PAUSED"


def test_tenant_pause_overrides_agent_on():
    decision = evaluate_control_policy(
        tenant_paused=True,
        desired_state="on",
    )
    assert decision.allowed is False
    assert (
        decision.reason_code
        == "TENANT_AUTOMATION_PAUSED"
    )
