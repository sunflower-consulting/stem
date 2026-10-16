# stem

Measure whether an attack on an LLM application actually worked, against a control, proved on a channel the target does not control.

```bash
pipx install sunflower-stem
stem demo
```

No API key. No configuration. No target of your own: `stem` ships the target it attacks.

> **Status: in development.** The build is landing slice by slice and this README grows with it.
> `stem doctor` is the authoritative statement of what the installed version can and cannot prove.

## What it does differently

Most tools in this space ask a model a question, show the reply to another model, and call the verdict a finding.
That produces three problems this tool is built to avoid.

**A hit with nothing to compare it to is not a measurement.**
Every case here carries a benign twin, so a result is the difference between what the target does under attack and what it does when nobody is attacking it.
Without that, a model which was always going to answer the question looks like a vulnerability.

**Proof is ranked, and the strongest available rung is what gets reported.**
A model emitting a plausible-looking string is the weakest thing this tool will call evidence, and it labels it as such.
The strongest is the target's own outbound request arriving at a listener the tester controls, which is proof that data moved rather than proof that a sentence was generated.

**Authorization is decided outside the model.**
The model proposes and a policy gate decides, so a case cannot talk its way into a request nobody signed.

## What it does not do

- It does not derive a severity score. Combining the signals it has would produce something that resembles a CVSS score, is not one, and would be the least defensible line in any output.
- It does not lead on breadth of attack catalogue. Other tools have far more techniques and say so accurately.
- It does not ship a calibrated model-graded verdict. The judge rung exists, is off by default, and `stem doctor` explains why.

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Authorized targets only.
