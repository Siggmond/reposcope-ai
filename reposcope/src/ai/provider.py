from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiInsight:
    title: str
    rationale: str


class AiProvider:
    def enabled(self) -> bool:
        return False

    def explain_architecture(self, *, architecture: dict) -> str | None:
        return None

    def explain_risk(self, *, file_path: str, reason: str, excerpt: str | None = None) -> AiInsight | None:
        return None
