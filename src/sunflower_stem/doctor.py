"""What this installation can and cannot prove.

Written because every claim this tool makes is conditional on something: a rung
needs a listener bound, a p-value needs a control arm, the judge needs a
calibration figure that does not exist yet. A user who runs one command and
reads one screen should come away knowing which of those hold for them, rather
than discovering it from a finding they cannot defend.
"""
from __future__ import annotations

import platform
import sys

from sunflower_stem import __version__

#: The judge rung is present, off, and uncalibrated. Stated here rather than
#: buried in docs because shipping a model-graded verdict as a default is how
#: the rest of this field produces findings a human then rejects: the rehearsal
#: that measured ours had every rubric firing too eagerly against a hardened
#: assistant. Until agreement-with-human is measured per rubric, the honest
#: default is off, and the four rungs above it need no model at all.
JUDGE_DEFAULT = False
JUDGE_REASON = ("present but OFF and uncalibrated: judge-versus-human agreement "
                "has not been measured per rubric, so a verdict from it is not "
                "defensible yet. The rungs above it need no model.")


def _rungs() -> list[str]:
    """The ladder, strongest first, each with what it needs to be reachable.

    Reported because a rung that cannot fire is the difference between a clean
    result and an untested one, and a reader who does not know which rungs were
    available cannot tell those apart from the output.
    """
    from sunflower_stem.schemas.finding import EvidenceStrength

    needs = {
        "CANARY": "a seeded token the target should not be able to produce",
        "CALLBACK": "a listener the target can reach; proof is its own request",
        "TOOL_CALL": "a target that reports the tools it invoked",
        "STRUCTURAL": "nothing: a deterministic matcher",
        "JUDGE": "a second model, and a calibration figure that does not exist yet",
    }
    out = []
    for s in sorted(EvidenceStrength, key=lambda s: -s.value):
        if s.name in needs:
            state = "off" if s.name == "JUDGE" and not JUDGE_DEFAULT else "available"
            out.append(f"  {s.value}  {s.name:<11} {state:<10} needs {needs[s.name]}")
    return out


def report() -> str:
    """A plain-text readout. No colour: this gets pasted into tickets."""
    from sunflower_stem.redact import REDACTION_VERSION

    lines = [
        f"stem {__version__}",
        f"python {platform.python_version()} on {sys.platform}",
        "",
        "API key required:      no. stem ships its own target; see `stem lab`.",
        ("Network required:      no. The bundled target and the callback "
         "listener both bind loopback."),
        (f"Redaction policy:      version {REDACTION_VERSION}, applied to the "
         f"run log and the evidence store."),
        "",
        "Evidence ladder, strongest first:",
        *_rungs(),
        "",
        f"judge rung:            {JUDGE_REASON}",
    ]
    return "\n".join(lines)
