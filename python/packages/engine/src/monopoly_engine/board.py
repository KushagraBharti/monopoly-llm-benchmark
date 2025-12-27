from __future__ import annotations

from .models import SpaceState


BOARD_SPEC: list[tuple[int, str, str, str | None, int | None]] = [
    (0, "GO", "Go", None, None),
    (1, "PROPERTY", "Mediterranean Avenue", "BROWN", 60),
    (2, "COMMUNITY_CHEST", "Community Chest", None, None),
    (3, "PROPERTY", "Baltic Avenue", "BROWN", 60),
    (4, "TAX", "Income Tax", None, None),
    (5, "RAILROAD", "Reading Railroad", "RAILROAD", 200),
    (6, "PROPERTY", "Oriental Avenue", "LIGHT_BLUE", 100),
    (7, "CHANCE", "Chance", None, None),
    (8, "PROPERTY", "Vermont Avenue", "LIGHT_BLUE", 100),
    (9, "PROPERTY", "Connecticut Avenue", "LIGHT_BLUE", 120),
    (10, "JAIL", "Jail", None, None),
    (11, "PROPERTY", "St. Charles Place", "PINK", 140),
    (12, "UTILITY", "Electric Company", "UTILITY", 150),
    (13, "PROPERTY", "States Avenue", "PINK", 140),
    (14, "PROPERTY", "Virginia Avenue", "PINK", 160),
    (15, "RAILROAD", "Pennsylvania Railroad", "RAILROAD", 200),
    (16, "PROPERTY", "St. James Place", "ORANGE", 180),
    (17, "COMMUNITY_CHEST", "Community Chest", None, None),
    (18, "PROPERTY", "Tennessee Avenue", "ORANGE", 180),
    (19, "PROPERTY", "New York Avenue", "ORANGE", 200),
    (20, "FREE_PARKING", "Free Parking", None, None),
    (21, "PROPERTY", "Kentucky Avenue", "RED", 220),
    (22, "CHANCE", "Chance", None, None),
    (23, "PROPERTY", "Indiana Avenue", "RED", 220),
    (24, "PROPERTY", "Illinois Avenue", "RED", 240),
    (25, "RAILROAD", "B. & O. Railroad", "RAILROAD", 200),
    (26, "PROPERTY", "Atlantic Avenue", "YELLOW", 260),
    (27, "PROPERTY", "Ventnor Avenue", "YELLOW", 260),
    (28, "UTILITY", "Water Works", "UTILITY", 150),
    (29, "PROPERTY", "Marvin Gardens", "YELLOW", 280),
    (30, "GO_TO_JAIL", "Go To Jail", None, None),
    (31, "PROPERTY", "Pacific Avenue", "GREEN", 300),
    (32, "PROPERTY", "North Carolina Avenue", "GREEN", 300),
    (33, "COMMUNITY_CHEST", "Community Chest", None, None),
    (34, "PROPERTY", "Pennsylvania Avenue", "GREEN", 320),
    (35, "RAILROAD", "Short Line", "RAILROAD", 200),
    (36, "CHANCE", "Chance", None, None),
    (37, "PROPERTY", "Park Place", "DARK_BLUE", 350),
    (38, "TAX", "Luxury Tax", None, None),
    (39, "PROPERTY", "Boardwalk", "DARK_BLUE", 400),
]


def build_board() -> list[SpaceState]:
    return [
        SpaceState(index=index, kind=kind, name=name, group=group, price=price)
        for index, kind, name, group, price in BOARD_SPEC
    ]
