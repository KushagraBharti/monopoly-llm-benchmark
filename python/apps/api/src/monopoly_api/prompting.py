from __future__ import annotations

from monopoly_arena import prompting as _impl
from monopoly_arena.prompting import (  # noqa: F401
    PromptBundle,
    PromptMemory,
    build_openrouter_tools,
    build_prompt_bundle,
    build_space_key_by_index,
)

__all__ = [
    "PromptBundle",
    "PromptMemory",
    "build_openrouter_tools",
    "build_prompt_bundle",
    "build_space_key_by_index",
]


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(dir(_impl)))

