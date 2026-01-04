from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterable, Awaitable, Callable

from monopoly_engine import Engine
from monopoly_telemetry import RunFiles, build_summary

from .openrouter_client import OpenRouterClient, OpenRouterResult

from .action_validation import validate_action_payload
from .player_config import EXPECTED_PLAYER_COUNT, PlayerConfig
from .prompting import (
    PromptBundle,
    PromptMemory,
    build_openrouter_tools,
    build_prompt_bundle,
    build_space_key_by_index,
)


DecisionCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class DecisionAttempt:
    prompt_messages: list[dict[str, Any]]
    prompt_payload: dict[str, Any] | None
    prompt_payload_raw: str | None
    raw_response: dict[str, Any] | None
    assistant_content: str | None
    parsed_tool_call: dict[str, Any] | None
    validation_errors: list[str]
    openrouter_request_id: str | None
    openrouter_status_code: int | None
    error_type: str | None
    error_message: str | None
    request_start_ms: int | None
    response_end_ms: int | None
    latency_ms: int | None


@dataclass(slots=True)
class DecisionOutcome:
    action: dict[str, Any]
    decision_meta: dict[str, Any]
    attempts: list[DecisionAttempt]
    retry_used: bool
    fallback_used: bool
    fallback_reason: str | None


@dataclass(slots=True)
class PendingResolution:
    decision: dict[str, Any]
    outcome: DecisionOutcome


class LlmRunner:
    def __init__(
        self,
        *,
        seed: int,
        players: list[PlayerConfig],
        run_id: str,
        openrouter: OpenRouterClient,
        run_files: RunFiles | None = None,
        max_turns: int = 200,
        event_delay_s: float = 0.25,
        start_ts_ms: int = 0,
        ts_step_ms: int = 250,
    ) -> None:
        self.run_id = run_id
        if len(players) != EXPECTED_PLAYER_COUNT:
            raise ValueError(f"Exactly {EXPECTED_PLAYER_COUNT} players are required for LLM runs.")
        self._player_configs = {player.player_id: player for player in players}
        self._openrouter = openrouter
        self._run_files = run_files
        self._engine = Engine(
            seed=seed,
            players=[{"player_id": p.player_id, "name": p.name} for p in players],
            run_id=run_id,
            max_turns=max_turns,
            start_ts_ms=start_ts_ms,
            ts_step_ms=ts_step_ms,
        )
        self._event_delay_s = event_delay_s
        self._space_key_by_index = build_space_key_by_index()
        self._prompt_memory = PromptMemory(space_key_by_index=self._space_key_by_index)
        self._paused = False
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._pending_resolution: PendingResolution | None = None
        self._advance_lock = asyncio.Lock()
        self._applied_decision_ids: set[str] = set()

    def request_stop(self, reason: str = "STOPPED") -> None:
        self._engine.request_stop(reason)
        self.resume()

    def pause(self) -> None:
        self._paused = True
        self._resume_event.clear()

    def resume(self) -> None:
        self._paused = False
        self._resume_event.set()

    def is_paused(self) -> bool:
        return self._paused

    def has_pending_resolution(self) -> bool:
        return self._pending_resolution is not None

    def get_snapshot(self) -> dict[str, Any]:
        return self._engine.get_snapshot()

    async def run(
        self,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_snapshot: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_summary: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_decision: DecisionCallback | None = None,
    ) -> None:
        event_handler = on_event
        snapshot_handler = on_snapshot
        summary_handler = on_summary
        if self._run_files is not None:
            run_files = self._run_files
            if event_handler is None:
                async def _write_event(event: dict[str, Any]) -> None:
                    run_files.write_event(event)

                event_handler = _write_event
            if snapshot_handler is None:
                async def _write_snapshot(snapshot: dict[str, Any]) -> None:
                    run_files.write_snapshot(snapshot)

                snapshot_handler = _write_snapshot
            if summary_handler is None:
                async def _write_summary(summary: dict[str, Any]) -> None:
                    run_files.write_summary(summary)

                summary_handler = _write_summary
        try:
            async for event in self._event_stream(on_decision=on_decision):
                if event_handler is not None:
                    await event_handler(event)
                if snapshot_handler is not None and event["type"] in {
                    "LLM_DECISION_REQUESTED",
                    "TURN_ENDED",
                    "GAME_ENDED",
                }:
                    await snapshot_handler(self.get_snapshot())
            if self._event_delay_s > 0:
                await asyncio.sleep(self._event_delay_s)
            if summary_handler is not None:
                if self._run_files is not None:
                    await summary_handler(build_summary(self._run_files))
                else:
                    await summary_handler(self._engine.build_summary())
        finally:
            await self._close_openrouter()

    async def _event_stream(
        self,
        on_decision: DecisionCallback | None = None,
    ) -> AsyncIterable[dict[str, Any]]:
        async def write_decision(entry: dict[str, Any]) -> None:
            if on_decision is not None:
                await on_decision(entry)
            elif self._run_files is not None:
                self._run_files.write_decision(entry)

        while True:
            await self._await_resume()
            async with self._advance_lock:
                _, events, decision, _ = self._engine.advance_until_decision(max_steps=1)
            if not events and decision is None:
                break
            for event in events:
                await self._await_resume()
                self._prompt_memory.update(event)
                yield event
            if decision is not None:
                await self._await_resume()
                outcome = await self._resolve_decision(decision, write_decision)
                self._pending_resolution = PendingResolution(decision=decision, outcome=outcome)
                await self._await_resume()
                pending = self._pending_resolution
                self._pending_resolution = None
                if pending is None:
                    continue
                decision = pending.decision
                outcome = self._validate_outcome_after_pause(decision, pending.outcome)
                async with self._advance_lock:
                    decision_id = decision["decision_id"]
                    if decision_id in self._applied_decision_ids:
                        raise RuntimeError(f"Decision {decision_id} already applied.")
                    _, action_events, _, _ = self._engine.apply_action(
                        outcome.action,
                        decision_meta=outcome.decision_meta,
                    )
                    self._applied_decision_ids.add(decision_id)
                if self._run_files is not None:
                    self._run_files.write_action(
                        {
                            "decision_id": decision["decision_id"],
                            "actor_player_id": decision["player_id"],
                            "decision_type": decision["decision_type"],
                            "turn_index": decision["turn_index"],
                            "action": outcome.action,
                        }
                    )
                player_config = self._player_configs[decision["player_id"]]
                resolved_entry = self._build_decision_log_entry(
                    decision=decision,
                    player_config=player_config,
                    phase="decision_resolved",
                    action=outcome.action,
                    attempts=outcome.attempts,
                    retry_used=outcome.retry_used,
                    fallback_used=outcome.fallback_used,
                    fallback_reason=outcome.fallback_reason,
                    action_events=action_events,
                    applied=True,
                )
                await write_decision(resolved_entry)
                for event in action_events:
                    await self._await_resume()
                    self._prompt_memory.update(event)
                    yield event
                if self._engine.is_game_over():
                    break
                continue
            if self._engine.is_game_over():
                break

    async def _resolve_decision(
        self,
        decision: dict[str, Any],
        log_writer: DecisionCallback | None,
    ) -> DecisionOutcome:
        player_id = decision["player_id"]
        player_config = self._player_configs[player_id]
        attempts: list[DecisionAttempt] = []
        artifact_attempts: list[dict[str, Any]] = []

        async def emit(entry: dict[str, Any]) -> None:
            if log_writer is not None:
                await log_writer(entry)

        prompt_bundle = build_prompt_bundle(
            decision,
            player_config,
            memory=self._prompt_memory,
            space_key_by_index=self._space_key_by_index,
        )
        tools = build_openrouter_tools(prompt_bundle.user_payload["decision"])

        def response_payload(result: OpenRouterResult | None) -> dict[str, Any]:
            if result is None:
                return {
                    "ok": False,
                    "status_code": None,
                    "request_id": None,
                    "error_type": "no_request",
                    "error": "No OpenRouter request was made",
                }
            if result.response_json is not None:
                return result.response_json
            return {
                "ok": False,
                "status_code": result.status_code,
                "request_id": result.request_id,
                "error_type": result.error_type,
                "error": result.error,
            }

        def write_artifacts(outcome: DecisionOutcome) -> None:
            if self._run_files is None:
                return
            for item in artifact_attempts:
                attempt_index = int(item.get("attempt_index", 0))
                prompt_item = item.get("prompt_bundle")
                if not isinstance(prompt_item, PromptBundle):
                    continue
                attempt_item = item.get("attempt")
                tool_action = item.get("action")
                validation_errors = item.get("errors")
                if not isinstance(validation_errors, list):
                    validation_errors = []
                error_reason = item.get("error_reason")
                parsed = {
                    "schema_version": "v1",
                    "decision_id": decision["decision_id"],
                    "attempt_index": attempt_index,
                    "parsed_tool_call": attempt_item.parsed_tool_call
                    if isinstance(attempt_item, DecisionAttempt)
                    else None,
                    "validation_errors": validation_errors,
                    "error_reason": error_reason,
                    "tool_action": tool_action,
                    "openrouter_request_id": attempt_item.openrouter_request_id
                    if isinstance(attempt_item, DecisionAttempt)
                    else None,
                    "openrouter_status_code": attempt_item.openrouter_status_code
                    if isinstance(attempt_item, DecisionAttempt)
                    else None,
                    "openrouter_error_type": attempt_item.error_type
                    if isinstance(attempt_item, DecisionAttempt)
                    else None,
                    "final_action": outcome.action,
                    "retry_used": outcome.retry_used,
                    "fallback_used": outcome.fallback_used,
                    "fallback_reason": outcome.fallback_reason,
                }
                self._run_files.write_prompt_artifacts(
                    decision_id=decision["decision_id"],
                    attempt_index=attempt_index,
                    system_prompt=prompt_item.system_prompt,
                    user_payload=prompt_item.user_payload,
                    tools=tools,
                    response=response_payload(item.get("result")),
                    parsed=parsed,
                )

        if not tools:
            fallback_action = self._fallback_action(decision)
            outcome = self._build_decision_outcome(
                decision=decision,
                action=fallback_action,
                attempts=attempts,
                retry_used=False,
                fallback_used=True,
                fallback_reason="unknown",
            )
            artifact_attempts.append(
                {
                    "attempt_index": 0,
                    "prompt_bundle": prompt_bundle,
                    "result": None,
                    "attempt": None,
                    "action": None,
                    "errors": ["No tools generated"],
                    "error_reason": "no_tools",
                }
            )
            write_artifacts(outcome)
            return outcome

        request_start_ms = _now_ms()
        await emit(
            self._build_decision_log_entry(
                decision=decision,
                player_config=player_config,
                phase="decision_started",
                action=None,
                attempts=[],
                retry_used=False,
                fallback_used=False,
                fallback_reason=None,
                request_start_ms=request_start_ms,
                prompt_messages=prompt_bundle.messages,
                prompt_payload=prompt_bundle.user_payload,
                prompt_payload_raw=prompt_bundle.user_content,
            )
        )
        if player_config.reasoning is not None:
            result = await self._openrouter.create_chat_completion(
                model=player_config.openrouter_model_id,
                messages=prompt_bundle.messages,
                tools=tools,
                tool_choice="required",
                reasoning=player_config.reasoning,
            )
        else:
            result = await self._openrouter.create_chat_completion(
                model=player_config.openrouter_model_id,
                messages=prompt_bundle.messages,
                tools=tools,
                tool_choice="required",
            )
        response_end_ms = _now_ms()
        attempt = self._attempt_from_response(
            prompt_bundle,
            result,
            request_start_ms,
            response_end_ms,
            include_prompt=False,
        )
        attempts.append(attempt)
        action, errors, error_reason = self._build_action_from_attempt(decision, attempt)
        artifact_attempts.append(
            {
                "attempt_index": 0,
                "prompt_bundle": prompt_bundle,
                "result": result,
                "attempt": attempt,
                "action": action,
                "errors": list(attempt.validation_errors),
                "error_reason": error_reason,
            }
        )
        if not result.ok and result.error_type != "invalid_json":
            fallback_reason = _map_openrouter_error(result.error_type)
            fallback = self._fallback_action(decision)
            outcome = self._build_decision_outcome(
                decision=decision,
                action=fallback,
                attempts=attempts,
                retry_used=False,
                fallback_used=True,
                fallback_reason=fallback_reason,
            )
            write_artifacts(outcome)
            return outcome
        if errors:
            retry_bundle = build_prompt_bundle(
                decision,
                player_config,
                memory=self._prompt_memory,
                space_key_by_index=self._space_key_by_index,
                retry_errors=errors,
            )
            retry_start_ms = _now_ms()
            if player_config.reasoning is not None:
                retry_result = await self._openrouter.create_chat_completion(
                    model=player_config.openrouter_model_id,
                    messages=retry_bundle.messages,
                    tools=tools,
                    tool_choice="required",
                    reasoning=player_config.reasoning,
                )
            else:
                retry_result = await self._openrouter.create_chat_completion(
                    model=player_config.openrouter_model_id,
                    messages=retry_bundle.messages,
                    tools=tools,
                    tool_choice="required",
                )
            retry_end_ms = _now_ms()
            retry_attempt = self._attempt_from_response(
                retry_bundle,
                retry_result,
                retry_start_ms,
                retry_end_ms,
                include_prompt=True,
            )
            attempts.append(retry_attempt)
            retry_action, retry_errors, retry_error_reason = self._build_action_from_attempt(
                decision,
                retry_attempt,
            )
            artifact_attempts.append(
                {
                    "attempt_index": 1,
                    "prompt_bundle": retry_bundle,
                    "result": retry_result,
                    "attempt": retry_attempt,
                    "action": retry_action,
                    "errors": list(retry_attempt.validation_errors),
                    "error_reason": retry_error_reason,
                }
            )
            if not retry_result.ok and retry_result.error_type != "invalid_json":
                fallback_reason = _map_openrouter_error(retry_result.error_type)
                fallback = self._fallback_action(decision)
                outcome = self._build_decision_outcome(
                    decision=decision,
                    action=fallback,
                    attempts=attempts,
                    retry_used=True,
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                )
                write_artifacts(outcome)
                return outcome
            if retry_errors:
                fallback_reason = retry_error_reason or "invalid_action"
                fallback = self._fallback_action(decision)
                outcome = self._build_decision_outcome(
                    decision=decision,
                    action=fallback,
                    attempts=attempts,
                    retry_used=True,
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                )
                write_artifacts(outcome)
                return outcome
            outcome = self._build_decision_outcome(
                decision=decision,
                action=retry_action or self._fallback_action(decision),
                attempts=attempts,
                retry_used=True,
                fallback_used=False,
                fallback_reason=None,
            )
            write_artifacts(outcome)
            return outcome
        outcome = self._build_decision_outcome(
            decision=decision,
            action=action or self._fallback_action(decision),
            attempts=attempts,
            retry_used=False,
            fallback_used=False,
            fallback_reason=None,
        )
        write_artifacts(outcome)
        return outcome

    def _attempt_from_response(
        self,
        prompt: PromptBundle,
        result: OpenRouterResult,
        request_start_ms: int | None,
        response_end_ms: int | None,
        *,
        include_prompt: bool,
    ) -> DecisionAttempt:
        response_json = result.response_json if result.ok else None
        assistant_content = None
        tool_call = None
        errors: list[str] = []
        if response_json is None:
            errors.append(result.error or "OpenRouter error")
        else:
            assistant_content = (
                response_json.get("choices", [{}])[0].get("message", {}).get("content")
            )
            tool_call, parse_error = parse_tool_call(response_json)
            if parse_error:
                errors.append(parse_error)
        latency_ms = None
        if request_start_ms is not None and response_end_ms is not None:
            latency_ms = max(response_end_ms - request_start_ms, 0)
        prompt_messages: list[dict[str, Any]] = []
        prompt_payload = None
        prompt_payload_raw = None
        if include_prompt:
            prompt_messages = prompt.messages
            prompt_payload = prompt.user_payload
            prompt_payload_raw = prompt.user_content
        return DecisionAttempt(
            prompt_messages=prompt_messages,
            prompt_payload=prompt_payload,
            prompt_payload_raw=prompt_payload_raw,
            raw_response=response_json,
            assistant_content=assistant_content,
            parsed_tool_call=tool_call,
            validation_errors=errors,
            openrouter_request_id=result.request_id,
            openrouter_status_code=result.status_code,
            error_type=result.error_type,
            error_message=result.error,
            request_start_ms=request_start_ms,
            response_end_ms=response_end_ms,
            latency_ms=latency_ms,
        )

    def _build_action_from_attempt(
        self,
        decision: dict[str, Any],
        attempt: DecisionAttempt,
    ) -> tuple[dict[str, Any] | None, list[str], str | None]:
        if attempt.parsed_tool_call is None:
            errors = attempt.validation_errors or ["Missing tool call"]
            if not attempt.validation_errors:
                attempt.validation_errors.extend(errors)
            return None, errors, "invalid_tool_call"
        action = tool_call_to_action(decision, attempt.parsed_tool_call)
        if action is None:
            errors = ["Unable to map tool call to action"]
            attempt.validation_errors.extend(errors)
            return None, errors, "invalid_tool_call"
        errors = validate_decision_action(decision, action)
        if errors:
            attempt.validation_errors.extend(errors)
            return action, errors, "invalid_action"
        return action, [], None

    def _build_decision_outcome(
        self,
        *,
        decision: dict[str, Any],
        action: dict[str, Any],
        attempts: list[DecisionAttempt],
        retry_used: bool,
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> DecisionOutcome:
        decision_meta: dict[str, Any] = {"valid": True, "error": None}
        if fallback_used:
            decision_meta = {
                "valid": False,
                "error": f"fallback:{fallback_reason or 'unknown'}",
            }
        return DecisionOutcome(
            action=action,
            decision_meta=decision_meta,
            attempts=attempts,
            retry_used=retry_used,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    def _validate_outcome_after_pause(
        self,
        decision: dict[str, Any],
        outcome: DecisionOutcome,
    ) -> DecisionOutcome:
        errors = validate_decision_action(decision, outcome.action)
        if not errors:
            return outcome
        fallback_action = self._fallback_action(decision)
        return self._build_decision_outcome(
            decision=decision,
            action=fallback_action,
            attempts=outcome.attempts,
            retry_used=outcome.retry_used,
            fallback_used=True,
            fallback_reason="invalid_action_after_pause",
        )

    def _build_decision_log_entry(
        self,
        *,
        decision: dict[str, Any],
        player_config: PlayerConfig,
        phase: str,
        action: dict[str, Any] | None,
        attempts: list[DecisionAttempt],
        retry_used: bool,
        fallback_used: bool,
        fallback_reason: str | None,
        request_start_ms: int | None = None,
        prompt_messages: list[dict[str, Any]] | None = None,
        prompt_payload: dict[str, Any] | None = None,
        prompt_payload_raw: str | None = None,
        action_events: list[dict[str, Any]] | None = None,
        applied: bool | None = None,
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "phase": phase,
            "run_id": decision["run_id"],
            "turn_index": decision["turn_index"],
            "decision_id": decision["decision_id"],
            "decision_type": decision["decision_type"],
            "player_id": decision["player_id"],
            "player_name": player_config.name,
            "openrouter_model_id": player_config.openrouter_model_id,
            "model_display_name": player_config.model_display_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if player_config.reasoning is not None:
            entry["reasoning"] = player_config.reasoning
        if phase == "decision_started":
            entry["request_start_ms"] = request_start_ms
            entry["prompt_messages"] = prompt_messages or []
            entry["prompt_payload"] = prompt_payload
            entry["prompt_payload_raw"] = prompt_payload_raw
            return entry

        entry["attempts"] = [
            {
                "prompt_messages": attempt.prompt_messages,
                "prompt_payload": attempt.prompt_payload,
                "prompt_payload_raw": attempt.prompt_payload_raw,
                "raw_response": attempt.raw_response,
                "assistant_content": attempt.assistant_content,
                "parsed_tool_call": attempt.parsed_tool_call,
                "validation_errors": attempt.validation_errors,
                "openrouter_request_id": attempt.openrouter_request_id,
                "openrouter_status_code": attempt.openrouter_status_code,
                "error_type": attempt.error_type,
                "error_message": attempt.error_message,
                "request_start_ms": attempt.request_start_ms,
                "response_end_ms": attempt.response_end_ms,
                "latency_ms": attempt.latency_ms,
            }
            for attempt in attempts
        ]
        entry["retry_used"] = retry_used
        entry["fallback_used"] = fallback_used
        entry["fallback_reason"] = fallback_reason
        entry["final_action"] = action
        if fallback_used:
            entry["fallback_action"] = action
        if applied is not None:
            entry["applied"] = applied
        if action_events is not None:
            event_ids = [event.get("event_id") for event in action_events]
            event_types = [event.get("type") for event in action_events]
            seqs: list[int] = []
            for event in action_events:
                seq = event.get("seq")
                if isinstance(seq, int):
                    seqs.append(seq)
            entry["emitted_event_ids"] = event_ids
            entry["emitted_event_types"] = event_types
            if seqs:
                entry["emitted_event_seq_start"] = min(seqs)
                entry["emitted_event_seq_end"] = max(seqs)
        decision_start_ms = request_start_ms
        if decision_start_ms is None and attempts:
            decision_start_ms = attempts[0].request_start_ms
        decision_end_ms = attempts[-1].response_end_ms if attempts else None
        if decision_start_ms is not None:
            entry["request_start_ms"] = decision_start_ms
        if decision_end_ms is not None:
            entry["response_end_ms"] = decision_end_ms
        if decision_start_ms is not None and decision_end_ms is not None:
            entry["latency_ms"] = max(decision_end_ms - decision_start_ms, 0)
        return entry

    def _fallback_action(self, decision: dict[str, Any]) -> dict[str, Any]:
        legal_actions = [entry["action"] for entry in decision.get("legal_actions", []) if entry.get("action")]
        decision_id = decision["decision_id"]

        def first_space_key(indices: list[int] | None) -> str | None:
            if not indices:
                return None
            index = int(indices[0])
            return self._space_key_by_index.get(index, f"SPACE_{index}")

        post_turn = decision.get("post_turn", {})
        post_options = post_turn.get("options", {}) if isinstance(post_turn, dict) else {}
        liquidation = decision.get("liquidation", {})
        liq_options = liquidation.get("options", {}) if isinstance(liquidation, dict) else {}

        if decision.get("decision_type") == "AUCTION_BID_DECISION":
            auction = decision.get("state", {}).get("auction", {})
            current_high_bid = int(auction.get("current_high_bid", 0) or 0)
            min_next_bid = current_high_bid + 1
            player_cash = None
            action_name = "NOOP"
            auction_args: dict[str, Any] = {"reason": "fallback"}
            for player in decision.get("state", {}).get("players", []):
                if player.get("player_id") == decision.get("player_id"):
                    player_cash = int(player.get("cash", 0))
                    break
            if "bid_auction" in legal_actions and player_cash is not None and player_cash >= min_next_bid:
                action_name = "bid_auction"
                auction_args = {"bid_amount": min_next_bid}
            elif "drop_out" in legal_actions:
                action_name = "drop_out"
                auction_args = {}
            elif legal_actions:
                action_name = legal_actions[0]
                auction_args = {}
            return {
                "schema_version": "v1",
                "decision_id": decision_id,
                "action": action_name,
                "args": auction_args,
            }
        if decision.get("decision_type") == "TRADE_RESPONSE_DECISION":
            if "reject_trade" in legal_actions:
                return {
                    "schema_version": "v1",
                    "decision_id": decision_id,
                    "action": "reject_trade",
                    "args": {},
                }
            if "accept_trade" in legal_actions:
                return {
                    "schema_version": "v1",
                    "decision_id": decision_id,
                    "action": "accept_trade",
                    "args": {},
                }
            if "counter_trade" in legal_actions:
                return {
                    "schema_version": "v1",
                    "decision_id": decision_id,
                    "action": "counter_trade",
                    "args": {
                        "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                        "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                    },
                }
        if decision.get("decision_type") == "TRADE_PROPOSE_DECISION":
            if "propose_trade" in legal_actions:
                players = decision.get("state", {}).get("players", [])
                actor_id = decision.get("player_id")
                target_id = None
                for entry in players:
                    if entry.get("player_id") != actor_id and not entry.get("bankrupt"):
                        target_id = entry.get("player_id")
                        break
                if target_id:
                    return {
                        "schema_version": "v1",
                        "decision_id": decision_id,
                        "action": "propose_trade",
                        "args": {
                            "to_player_id": target_id,
                            "offer": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                            "request": {"cash": 0, "properties": [], "get_out_of_jail_cards": 0},
                        },
                    }

        def build_plan_args(indices: list[int] | None) -> dict[str, Any] | None:
            if not indices:
                return None
            space_key = first_space_key(indices)
            if space_key is None:
                return None
            board = decision.get("state", {}).get("board", [])
            matching: dict[str, Any] = next(
                (space for space in board if space.get("index") == indices[0]),
                {},
            )
            houses = int(matching.get("houses", 0))
            hotel = bool(matching.get("hotel", False))
            kind = "HOTEL" if hotel or houses >= 4 else "HOUSE"
            return {"build_plan": [{"space_key": space_key, "kind": kind, "count": 1}]}

        def sell_plan_args(indices: list[int] | None) -> dict[str, Any] | None:
            if not indices:
                return None
            space_key = first_space_key(indices)
            if space_key is None:
                return None
            board = decision.get("state", {}).get("board", [])
            matching: dict[str, Any] = next(
                (space for space in board if space.get("index") == indices[0]),
                {},
            )
            hotel = bool(matching.get("hotel", False))
            kind = "HOTEL" if hotel else "HOUSE"
            return {"sell_plan": [{"space_key": space_key, "kind": kind, "count": 1}]}

        action_name = "NOOP"
        args: dict[str, Any] = {"reason": "fallback"}
        if "buy_property" in legal_actions:
            action_name = "buy_property"
            args = {}
        elif "start_auction" in legal_actions:
            action_name = "start_auction"
            args = {}
        elif "end_turn" in legal_actions:
            action_name = "end_turn"
            args = {}
        elif "declare_bankruptcy" in legal_actions:
            action_name = "declare_bankruptcy"
            args = {}
        elif "mortgage_property" in legal_actions:
            space_key = first_space_key(
                post_options.get("mortgageable_space_indices")
                or liq_options.get("mortgageable_space_indices")
            )
            if space_key:
                action_name = "mortgage_property"
                args = {"space_key": space_key}
            else:
                action_name = "declare_bankruptcy"
                args = {}
        elif "unmortgage_property" in legal_actions:
            space_key = first_space_key(post_options.get("unmortgageable_space_indices"))
            if space_key:
                action_name = "unmortgage_property"
                args = {"space_key": space_key}
            else:
                action_name = "end_turn"
                args = {}
        elif "sell_houses_or_hotel" in legal_actions:
            args_payload = sell_plan_args(
                post_options.get("sellable_building_space_indices")
                or liq_options.get("sellable_building_space_indices")
            )
            if args_payload:
                action_name = "sell_houses_or_hotel"
                args = args_payload
            elif "declare_bankruptcy" in legal_actions:
                action_name = "declare_bankruptcy"
                args = {}
            else:
                action_name = "end_turn"
                args = {}
        elif "build_houses_or_hotel" in legal_actions:
            args_payload = build_plan_args(post_options.get("buildable_space_indices"))
            if args_payload:
                action_name = "build_houses_or_hotel"
                args = args_payload
            else:
                action_name = "end_turn"
                args = {}
        elif legal_actions:
            action_name = legal_actions[0]
            args = {}
        return {
            "schema_version": "v1",
            "decision_id": decision_id,
            "action": action_name,
            "args": args,
        }

    async def _close_openrouter(self) -> None:
        close = getattr(self._openrouter, "aclose", None)
        if close is None:
            return
        result = close()
        if asyncio.iscoroutine(result):
            await result

    async def _await_resume(self) -> None:
        if self._resume_event.is_set():
            return
        await self._resume_event.wait()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _map_openrouter_error(error_type: str | None) -> str:
    mapping = {
        "no_api_key": "no_api_key",
        "http_429": "openrouter_http_429",
        "http_5xx": "openrouter_http_5xx",
        "http_4xx": "openrouter_http_4xx",
        "network_error": "openrouter_network_error",
        "invalid_json": "invalid_tool_call",
    }
    if error_type is None:
        return "unknown"
    return mapping.get(error_type, "unknown")


def parse_tool_call(response_json: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    choices = response_json.get("choices", [])
    if not choices:
        return None, "No choices in response"
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        call = tool_calls[0]
        func = call.get("function", {})
        return {
            "name": func.get("name"),
            "arguments": func.get("arguments"),
        }, None
    function_call = message.get("function_call")
    if function_call:
        return {
            "name": function_call.get("name"),
            "arguments": function_call.get("arguments"),
        }, None
    return None, "No tool call found"


def tool_call_to_action(decision: dict[str, Any], tool_call: dict[str, Any]) -> dict[str, Any] | None:
    tool_name = tool_call.get("name")
    if not tool_name:
        return None
    legal_actions = [entry.get("action") for entry in decision.get("legal_actions", [])]
    action_name = _resolve_action_name(tool_name, legal_actions)
    if action_name is None:
        return None

    arguments = tool_call.get("arguments")
    if isinstance(arguments, str):
        try:
            args_payload = json.loads(arguments)
        except json.JSONDecodeError:
            return None
    elif isinstance(arguments, dict):
        args_payload = arguments
    else:
        args_payload = {}

    args = _filter_action_args(decision, action_name, args_payload)
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": action_name,
        "args": args,
    }
    if isinstance(args_payload, dict):
        if "public_message" in args_payload:
            action["public_message"] = args_payload.get("public_message")
        if "private_thought" in args_payload:
            action["private_thought"] = args_payload.get("private_thought")
    return action


def _resolve_action_name(tool_name: str, legal_actions: list[str | None]) -> str | None:
    allowed = {action for action in legal_actions if action}
    if tool_name in allowed:
        return tool_name
    candidate = tool_name.strip().upper().replace("-", "_")
    if candidate in allowed:
        return candidate
    return None


def _filter_action_args(
    decision: dict[str, Any],
    action_name: str,
    args_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(args_payload, dict):
        return {}
    args = dict(args_payload)
    args.pop("public_message", None)
    args.pop("private_thought", None)
    return args


def validate_decision_action(decision: dict[str, Any], action: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_ok, schema_errors = validate_action_payload(action)
    if not schema_ok:
        errors.extend(schema_errors)

    legal_actions = decision.get("legal_actions", [])
    allowed = {entry.get("action") for entry in legal_actions}
    if action.get("action") not in allowed:
        errors.append("Action not in legal_actions")

    return errors
