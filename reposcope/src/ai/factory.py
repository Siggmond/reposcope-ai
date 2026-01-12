from __future__ import annotations

import os

from reposcope.src.ai.noop import NoopAiProvider
from reposcope.src.ai.openai_provider import OpenAiProvider
from reposcope.src.ai.provider import AiProvider


def get_ai_provider(*, use_ai: bool) -> AiProvider:
    if not use_ai:
        return NoopAiProvider()

    api_key = os.environ.get("REPOSCOPE_OPENAI_API_KEY")
    if not api_key:
        return NoopAiProvider()

    return OpenAiProvider(api_key=api_key)
