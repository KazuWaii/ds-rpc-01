from unittest.mock import patch

from app.core.guardrails import contains_pii, is_out_of_scope, redact_pii
from app.services.llm import ChatResult


def test_contains_pii_detects_ssn():
    assert contains_pii("His SSN is 123-45-6789.") is True


def test_contains_pii_detects_phone():
    assert contains_pii("Call me at 555-123-4567.") is True


def test_contains_pii_false_on_clean_text():
    assert contains_pii("The leave policy allows 20 days per year.") is False


def test_contains_pii_ignores_emails():
    # Deliberate design choice: emails are legitimate business data here
    # (e.g. HR contact info), not something to redact.
    assert contains_pii("Contact hr@finsolve.com for details.") is False


def test_redact_pii_masks_ssn_and_phone():
    text = "Contact John at 555-123-4567 or his SSN is 123-45-6789."
    redacted = redact_pii(text)
    assert "555-123-4567" not in redacted
    assert "123-45-6789" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted


def test_redact_pii_leaves_clean_text_unchanged():
    text = "The leave policy allows 20 days per year."
    assert redact_pii(text) == text


def _fake_chat(content):
    def _chat(messages):
        return ChatResult(content=content, prompt_tokens=10, completion_tokens=2)

    return _chat


def test_is_out_of_scope_true_for_outofscope_verdict():
    with patch("app.core.guardrails.chat", side_effect=_fake_chat("OUTOFSCOPE")):
        assert is_out_of_scope("What is the capital of France?") is True


def test_is_out_of_scope_false_for_inscope_verdict():
    with patch("app.core.guardrails.chat", side_effect=_fake_chat("INSCOPE")):
        assert is_out_of_scope("What drove the increase in vendor expenses?") is False


def test_is_out_of_scope_tolerates_whitespace_and_case():
    with patch("app.core.guardrails.chat", side_effect=_fake_chat("  outofscope \n")):
        assert is_out_of_scope("anything") is True
