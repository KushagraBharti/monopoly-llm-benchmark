from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_STARTING_CASH = 1500
DEFAULT_HOUSES = 32
DEFAULT_HOTELS = 12


@dataclass(slots=True)
class SpaceState:
    index: int
    kind: str
    name: str
    group: str | None
    price: int | None
    owner_id: str | None = None
    mortgaged: bool = False
    houses: int = 0
    hotel: bool = False

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "name": self.name,
            "group": self.group,
            "price": self.price,
            "owner_id": self.owner_id,
            "mortgaged": self.mortgaged,
            "houses": self.houses,
            "hotel": self.hotel,
        }


@dataclass(slots=True)
class PlayerState:
    player_id: str
    name: str
    cash: int = DEFAULT_STARTING_CASH
    position: int = 0
    in_jail: bool = False
    jail_turns: int = 0
    doubles_count: int = 0
    bankrupt: bool = False
    bankrupt_to: str | None = None
    get_out_of_jail_cards: int = 0

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "cash": self.cash,
            "position": self.position,
            "in_jail": self.in_jail,
            "jail_turns": self.jail_turns,
            "doubles_count": self.doubles_count,
            "bankrupt": self.bankrupt,
            "bankrupt_to": self.bankrupt_to,
            "get_out_of_jail_cards": self.get_out_of_jail_cards,
        }


@dataclass(slots=True)
class BankState:
    houses_remaining: int = DEFAULT_HOUSES
    hotels_remaining: int = DEFAULT_HOTELS

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "houses_remaining": self.houses_remaining,
            "hotels_remaining": self.hotels_remaining,
        }


@dataclass(slots=True)
class GameState:
    run_id: str
    seed: int
    turn_index: int
    phase: str
    active_player_id: str
    players: list[PlayerState]
    bank: BankState
    board: list[SpaceState]

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "phase": self.phase,
            "active_player_id": self.active_player_id,
            "players": [player.to_snapshot() for player in self.players],
            "bank": self.bank.to_snapshot(),
            "board": [space.to_snapshot() for space in self.board],
        }
