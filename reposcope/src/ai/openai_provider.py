from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from reposcope.src.ai.provider import AiInsight, AiProvider


@dataclass(frozen=True)
class _OpenAiResult:
    content: str


class OpenAiProvider(AiProvider):
    def __init__(self, *, api_key: str):
        self._api_key = api_key
        self._model = os.environ.get("REPOSCOPE_OPENAI_MODEL", "gpt-4o-mini")

    def enabled(self) -> bool:
        return True

    def explain_architecture(self, *, architecture: dict) -> str | None:
        payload = {
            "task": "architecture_explanation",
            "architecture": architecture,
        }
        out = self._json_call(payload)
        if not out:
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return None

        text = data.get("explanation")
        if not isinstance(text, str):
            return None
        return text.strip() or None

    def explain_risk(self, *, file_path: str, reason: str, excerpt: str | None = None) -> AiInsight | None:
        payload = {
            "task": "risk_explanation",
            "file_path": file_path,
            "reason": reason,
            "excerpt": excerpt,
        }
        out = self._json_call(payload)
        if not out:
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return None

        title = data.get("title")
        rationale = data.get("rationale")
        if not isinstance(title, str) or not isinstance(rationale, str):
            return None

        title = title.strip()
        rationale = rationale.strip()
        if not title or not rationale:
            return None

        return AiInsight(title=title, rationale=rationale)

    def _json_call(self, payload: dict) -> str | None:
        try:
            result = self._chat_completions(payload)
        except Exception:
            return None

        return result.content

    def _chat_completions(self, payload: dict) -> _OpenAiResult:
        url = "https://api.openai.com/v1/chat/completions"

        system = (
            "You are a senior engineer writing short explanations for static analyzer findings. "
            "You MUST follow these rules:\n"
            "- Only explain the provided findings.\n"
            "- Do NOT discover new issues.\n"
            "- Do NOT guess frameworks, languages, or tools beyond the provided fields.\n"
            "- If information is insufficient, say so briefly.\n"
            "- Output MUST be valid JSON only. No markdown. No extra keys.\n"
        )

        if payload.get("task") == "risk_explanation":
            user = {
                "instruction": "Return JSON with keys: title, rationale.",
                "file_path": payload.get("file_path"),
                "reason": payload.get("reason"),
                "excerpt": payload.get("excerpt"),
            }
            response_format = {"type": "json_object"}
        elif payload.get("task") == "architecture_explanation":
            user = {
                "instruction": "Return JSON with key: explanation.",
                "architecture": payload.get("architecture"),
            }
            response_format = {"type": "json_object"}
        else:
            raise ValueError("Unknown task")

        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "response_format": response_format,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(raw) from e

        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("Invalid OpenAI response")

        return _OpenAiResult(content=content)
