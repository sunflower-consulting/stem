"""stem: measure whether an attack on an LLM application actually worked.

Three things distinguish a measurement here from a transcript somebody read:

  * every case has a benign twin, so a hit is compared against what the target
    does when nobody is attacking it. A rate without a control arm is an
    anecdote with a denominator.
  * proof is ranked, and the strongest available rung is what gets reported. A
    model emitting a plausible-looking string is the weakest thing this tool
    will call evidence, and it says so.
  * authorization is decided outside the model. The model proposes and the gate
    decides, so a case cannot talk its way into a request nobody signed.

The package is `sunflower_stem` and the command is `stem`; the names differ
because `stem` on PyPI is a Tor controller library that has every right to it.
"""

__version__ = "0.1.0.dev0"

__all__ = ["__version__"]
