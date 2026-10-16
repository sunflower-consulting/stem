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


def report() -> str:
    """A plain-text readout. No colour: this gets pasted into tickets."""
    lines = [
        f"stem {__version__}",
        f"python {platform.python_version()} on {sys.platform}",
        "",
        "API key required:      no. stem ships its own target; see `stem lab`.",
        ("Network required:      no. The bundled target and the callback "
         "listener both bind loopback."),
        "",
        f"judge rung:            {JUDGE_REASON}",
    ]
    return "\n".join(lines)
