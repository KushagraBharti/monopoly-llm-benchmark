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

PROPERTY_RENT_TABLES: dict[int, list[int]] = {
    1: [2, 10, 30, 90, 160, 250],
    3: [4, 20, 60, 180, 320, 450],
    6: [6, 30, 90, 270, 400, 550],
    8: [6, 30, 90, 270, 400, 550],
    9: [8, 40, 100, 300, 450, 600],
    11: [10, 50, 150, 450, 625, 750],
    13: [10, 50, 150, 450, 625, 750],
    14: [12, 60, 180, 500, 700, 900],
    16: [14, 70, 200, 550, 750, 950],
    18: [14, 70, 200, 550, 750, 950],
    19: [16, 80, 220, 600, 800, 1000],
    21: [18, 90, 250, 700, 875, 1050],
    23: [18, 90, 250, 700, 875, 1050],
    24: [20, 100, 300, 750, 925, 1100],
    26: [22, 110, 330, 800, 975, 1150],
    27: [22, 110, 330, 800, 975, 1150],
    29: [24, 120, 360, 850, 1025, 1200],
    31: [26, 130, 390, 900, 1100, 1275],
    32: [26, 130, 390, 900, 1100, 1275],
    34: [28, 150, 450, 1000, 1200, 1400],
    37: [35, 175, 500, 1100, 1300, 1500],
    39: [50, 200, 600, 1400, 1700, 2000],
}

RAILROAD_RENTS = [25, 50, 100, 200]
UTILITY_RENT_MULTIPLIER = {1: 4, 2: 10}
TAX_AMOUNTS = {4: 200, 38: 100}

OWNABLE_KINDS = {"PROPERTY", "RAILROAD", "UTILITY"}

GROUP_INDEXES: dict[str, list[int]] = {}
for index, kind, _, group, _ in BOARD_SPEC:
    if group:
        GROUP_INDEXES.setdefault(group, []).append(index)


def build_board() -> list[SpaceState]:
    return [
        SpaceState(index=index, kind=kind, name=name, group=group, price=price)
        for index, kind, name, group, price in BOARD_SPEC
    ]
