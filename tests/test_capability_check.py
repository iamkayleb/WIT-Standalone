"""Tests for capability_check.py — particularly that string input is handled correctly."""

from scripts.langchain.capability_check import check_capability, classify_capabilities


def test_classify_capabilities_with_list_input() -> None:
    """List input (normal programmatic use) works unchanged."""
    result = classify_capabilities(["Create a minimal change", "Validate pipeline"], "")
    assert result.actionable_tasks == ["Create a minimal change", "Validate pipeline"]
    assert result.recommendation == "PROCEED"


def test_classify_capabilities_with_bulleted_string_input() -> None:
    """String with bullet-point tasks is parsed correctly (workflow passes raw file text)."""
    tasks_text = "- Create a minimal change\n- Validate the intake automation pipeline\n"
    result = classify_capabilities(tasks_text, "Must work correctly")
    assert result.actionable_tasks == [
        "Create a minimal change",
        "Validate the intake automation pipeline",
    ]
    assert result.recommendation == "PROCEED"


def test_classify_capabilities_string_does_not_iterate_characters() -> None:
    """A raw task sentence must NOT produce one entry per character."""
    sentence = "Create a minimal change to validate the intake automation pipeline."
    result = classify_capabilities(sentence, "")
    # _parse_tasks_from_text only picks up bullet lines; a plain sentence yields
    # no tasks rather than ~60 individual characters.
    assert all(
        len(t) > 1 for t in result.actionable_tasks
    ), "Tasks should not be individual characters"


def test_check_capability_alias_accepts_string() -> None:
    """check_capability (workflow alias) must accept a string without error."""
    tasks_text = "- Task one\n- Task two\n"
    result = check_capability(tasks_text, "")
    assert len(result.actionable_tasks) == 2


def test_classify_capabilities_empty_string() -> None:
    """Empty string input returns REVIEW_NEEDED (no tasks detected)."""
    result = classify_capabilities("", "")
    assert result.actionable_tasks == []
    assert result.recommendation == "REVIEW_NEEDED"


def test_fallback_does_not_expose_llm_diagnostic_as_human_action() -> None:
    """Infrastructure reasons like 'LLM provider unavailable' must NOT appear in
    human_actions_needed — they are diagnostic messages, not actions for humans."""
    # Without API keys the fallback path is always taken in CI; none of the
    # diagnostic strings used there should surface as a required human action.
    result = classify_capabilities(["Create a minimal change", "Validate pipeline"], "")
    diagnostic_phrases = [
        "LLM provider unavailable",
        "langchain-core not installed",
        "LLM response missing JSON payload",
        "LLM response JSON parse failed",
    ]
    for phrase in diagnostic_phrases:
        assert phrase not in result.human_actions_needed, (
            f"Infrastructure message '{phrase}' must not appear in human_actions_needed"
        )


def test_fallback_empty_tasks_no_llm_diagnostic_in_human_actions() -> None:
    """Even with no tasks, 'LLM provider unavailable' must not appear as a human action."""
    result = classify_capabilities("", "")
    assert "LLM provider unavailable" not in result.human_actions_needed
