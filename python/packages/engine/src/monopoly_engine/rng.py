from __future__ import annotations

import random


class DeterministicRng:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def roll_dice(self) -> tuple[int, int]:
        return self._rng.randint(1, 6), self._rng.randint(1, 6)
