"""`stem doctor` is the authoritative statement of what this install can prove.

Tested because it is the one output a reader is told to trust over the README,
and because its claims are the claims: if it says no key is needed while the
default path needs one, the tool is lying in the place it promised not to.
"""
from __future__ import annotations

from sunflower_stem.doctor import JUDGE_DEFAULT, report


def test_the_judge_rung_is_off_by_default():
    """The decision, pinned. Shipping a model-graded verdict on by default is
    how this field produces findings a human then rejects, and ours has never
    been measured against human agreement per rubric."""
    assert JUDGE_DEFAULT is False


def test_the_readout_says_no_api_key_is_needed():
    out = report()
    assert "API key required:      no" in out


def test_the_readout_explains_the_judge_rather_than_only_disabling_it():
    """A capability that is off without a reason reads as unfinished. This one
    is off on purpose and the readout has to carry the purpose."""
    out = report()
    assert "judge rung:" in out
    assert "uncalibrated" in out


def test_the_readout_names_every_rung_and_what_it_needs():
    """A rung that cannot fire is the difference between a clean result and an
    untested one. A reader who cannot see which rungs were reachable cannot
    tell those apart from the output."""
    out = report()
    for rung in ("CANARY", "CALLBACK", "TOOL_CALL", "STRUCTURAL", "JUDGE"):
        assert rung in out, f"{rung} missing from the readout"
    assert "needs a seeded token" in out


def test_the_readout_states_the_redaction_version():
    """Which policy was in force is what makes two runs comparable, so it is a
    fact about the installation rather than a detail of a run."""
    from sunflower_stem.redact import REDACTION_VERSION

    assert f"version {REDACTION_VERSION}" in report()


def test_the_readout_is_plain_text():
    """It gets pasted into tickets and issue trackers. No escape codes."""
    assert "\x1b[" not in report()
