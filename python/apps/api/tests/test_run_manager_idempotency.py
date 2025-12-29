from __future__ import annotations

import asyncio

from monopoly_engine import create_initial_state

from monopoly_api.player_config import DEFAULT_SYSTEM_PROMPT, PlayerConfig, derive_model_display_name
from monopoly_api.run_manager import RunManager


class FakeRunner:
    def __init__(
        self,
        *,
        seed: int,
        players: list[PlayerConfig],
        run_id: str,
        openrouter: object | None = None,
        run_files: object | None = None,
        **_: object,
    ) -> None:
        self.run_id = run_id
        self.run_calls = 0
        self.pause_calls = 0
        self.resume_calls = 0
        self._stop_event = asyncio.Event()
        self._snapshot = create_initial_state(
            run_id,
            seed,
            [{"player_id": player.player_id, "name": player.name} for player in players],
        ).to_snapshot()

    def request_stop(self, reason: str = "STOPPED") -> None:
        self._stop_event.set()

    def pause(self) -> None:
        self.pause_calls += 1

    def resume(self) -> None:
        self.resume_calls += 1

    def get_snapshot(self) -> dict[str, object]:
        return self._snapshot

    async def run(self, *_: object, **__: object) -> None:
        self.run_calls += 1
        await self._stop_event.wait()


def _make_players() -> list[PlayerConfig]:
    model_id = "openai/gpt-oss-120b"
    return [
        PlayerConfig(
            player_id="p1",
            name="P1",
            openrouter_model_id=model_id,
            model_display_name=derive_model_display_name(model_id),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            reasoning=None,
        ),
        PlayerConfig(
            player_id="p2",
            name="P2",
            openrouter_model_id=model_id,
            model_display_name=derive_model_display_name(model_id),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            reasoning=None,
        ),
        PlayerConfig(
            player_id="p3",
            name="P3",
            openrouter_model_id=model_id,
            model_display_name=derive_model_display_name(model_id),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            reasoning=None,
        ),
        PlayerConfig(
            player_id="p4",
            name="P4",
            openrouter_model_id=model_id,
            model_display_name=derive_model_display_name(model_id),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            reasoning=None,
        ),
    ]


def test_start_run_idempotent_when_running(tmp_path) -> None:
    async def run_test() -> None:
        runners: list[FakeRunner] = []

        def runner_factory(**kwargs: object) -> FakeRunner:
            runner = FakeRunner(**kwargs)
            runners.append(runner)
            return runner

        manager = RunManager(
            tmp_path,
            runner_factory=runner_factory,
            openrouter_factory=lambda: object(),
        )
        players = _make_players()
        run_id = await manager.start_run(seed=101, players=players)
        await asyncio.sleep(0)
        first_task = manager._runner_task
        first_runner = manager._runner

        second_run_id = await manager.start_run(seed=101, players=players)
        await asyncio.sleep(0)

        assert second_run_id == run_id
        assert manager._runner_task is first_task
        assert manager._runner is first_runner
        assert len(runners) == 1
        assert runners[0].run_calls == 1

        await manager.stop_run()

    asyncio.run(run_test())


def test_resume_is_idempotent(tmp_path) -> None:
    async def run_test() -> None:
        runners: list[FakeRunner] = []

        def runner_factory(**kwargs: object) -> FakeRunner:
            runner = FakeRunner(**kwargs)
            runners.append(runner)
            return runner

        manager = RunManager(
            tmp_path,
            runner_factory=runner_factory,
            openrouter_factory=lambda: object(),
        )
        players = _make_players()
        await manager.start_run(seed=202, players=players)
        await asyncio.sleep(0)

        await manager.resume()
        assert runners[0].resume_calls == 0

        await manager.pause()
        assert runners[0].pause_calls == 1

        await manager.resume()
        assert runners[0].resume_calls == 1

        await manager.resume()
        assert runners[0].resume_calls == 1

        await manager.stop_run()

    asyncio.run(run_test())
