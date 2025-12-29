from __future__ import annotations

import random
from typing import TypeVar


T = TypeVar("T")


class DeterministicRng:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def roll_dice(self) -> tuple[int, int]:
        return self._rng.randint(1, 6), self._rng.randint(1, 6)

    def shuffle(self, items: list[T]) -> list[T]:
        copied = list(items)
        self._rng.shuffle(copied)
        return copied
