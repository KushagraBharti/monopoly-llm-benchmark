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
class AuctionState:
    property_space_key: str
    property_space_index: int
    current_high_bid: int
    current_leader_player_id: str | None
    active_bidders_player_ids: list[str]
    current_bidder_index: int
    initiator_player_id: str
    turn_owner_player_id: str
    rolled_double: bool

    def to_snapshot(self) -> dict[str, Any]:
        current_bidder = None
        if self.active_bidders_player_ids:
            if 0 <= self.current_bidder_index < len(self.active_bidders_player_ids):
                current_bidder = self.active_bidders_player_ids[self.current_bidder_index]
            else:
                current_bidder = self.active_bidders_player_ids[0]
        return {
            "property_space_key": self.property_space_key,
            "current_high_bid": self.current_high_bid,
            "current_leader_player_id": self.current_leader_player_id,
            "active_bidders_player_ids": list(self.active_bidders_player_ids),
            "current_bidder_player_id": current_bidder,
            "initiator_player_id": self.initiator_player_id,
        }


@dataclass(slots=True)
class TradeBundle:
    cash: int
    properties: list[str]
    get_out_of_jail_cards: int

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "cash": int(self.cash),
            "properties": list(self.properties),
            "get_out_of_jail_cards": int(self.get_out_of_jail_cards),
        }


@dataclass(slots=True)
class TradeExchange:
    from_player_id: str
    offer: TradeBundle
    request: TradeBundle

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "from_player_id": self.from_player_id,
            "offer": self.offer.to_snapshot(),
            "request": self.request.to_snapshot(),
        }


@dataclass(slots=True)
class TradeThread:
    initiator_player_id: str
    counterparty_player_id: str
    max_exchanges: int
    exchange_index: int
    history: list[TradeExchange]
    current_offer: TradeExchange
    turn_owner_player_id: str
    rolled_double: bool

    def to_snapshot(self) -> dict[str, Any]:
        history_slice = self.history[-2:]
        return {
            "initiator_player_id": self.initiator_player_id,
            "counterparty_player_id": self.counterparty_player_id,
            "max_exchanges": self.max_exchanges,
            "exchange_index": self.exchange_index,
            "history_last_2": [entry.to_snapshot() for entry in history_slice],
            "current_offer": {
                "offer": self.current_offer.offer.to_snapshot(),
                "request": self.current_offer.request.to_snapshot(),
            },
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
    auction: AuctionState | None = None
    trade: TradeThread | None = None

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
            "auction": self.auction.to_snapshot() if self.auction is not None else None,
            "trade": self.trade.to_snapshot() if self.trade is not None else None,
        }
