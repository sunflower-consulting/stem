"""Real tool adapters -- deterministic runners that live *below* the agents.

A tool never decides whether it may run; the PolicyEngine does, and every call
reaches a tool only through ``AgentContext.execute_tool`` (which authorizes
first). A tool's job is narrow: do one bounded thing, write what it observed
into the content-addressed evidence store, and return a structured result that
references evidence by hash. No tool invents an external fact; lookups carry a
``source`` and ``retrieved_at`` so provenance survives into the knowledge graph.

The callable contract matches what ``AgentContext`` expects: ``tool(req) ->
dict``. The returned dict always includes ``evidence_refs``.
"""
from __future__ import annotations

import abc
import json

from sunflower_stem.evidence.store import EvidenceStore
from sunflower_stem.policy.decision import ToolRequest
from sunflower_stem.schemas.evidence import EvidenceKind
from sunflower_stem.schemas.target import ActionClass


class Tool(abc.ABC):
    """Base class for a gated, evidence-producing tool."""

    name: str = ""
    action_class: ActionClass = ActionClass.PASSIVE
    evidence_kind: EvidenceKind = EvidenceKind.LOG

    def __init__(self, store: EvidenceStore | None = None):
        self.store = store or EvidenceStore()

    def _record(self, data: bytes | None = None, *, obj=None,
                target: str = "", source: str | None = None, meta: dict | None = None) -> str:
        """Store evidence as a typed, provenanced item; return its content hash.

        The kind and producer come from the tool (``evidence_kind`` / ``name``),
        so a stored artifact always knows what it is and what made it.
        """
        if obj is not None:
            data = json.dumps(obj, sort_keys=True).encode()
        item = self.store.put_item(data or b"", kind=self.evidence_kind,
                                   produced_by=self.name, target=target,
                                   source=source, meta=meta)
        return item.sha256

    @abc.abstractmethod
    def __call__(self, req: ToolRequest) -> dict:
        ...
