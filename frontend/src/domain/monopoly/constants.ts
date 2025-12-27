import type { SpaceKind } from '../../net/contracts';

export type GroupKey =
  | 'BROWN'
  | 'LIGHT_BLUE'
  | 'PINK'
  | 'ORANGE'
  | 'RED'
  | 'YELLOW'
  | 'GREEN'
  | 'DARK_BLUE'
  | 'RAILROAD'
  | 'UTILITY';

export type BoardTile = {
  index: number;
  kind: SpaceKind;
  name: string;
  group: GroupKey | null;
  price: number | null;
};

export const BOARD_TILES: ReadonlyArray<BoardTile> = [
  { index: 0, kind: 'GO', name: 'Go', group: null, price: null },
  { index: 1, kind: 'PROPERTY', name: 'Mediterranean Avenue', group: 'BROWN', price: 60 },
  { index: 2, kind: 'COMMUNITY_CHEST', name: 'Community Chest', group: null, price: null },
  { index: 3, kind: 'PROPERTY', name: 'Baltic Avenue', group: 'BROWN', price: 60 },
  { index: 4, kind: 'TAX', name: 'Income Tax', group: null, price: null },
  { index: 5, kind: 'RAILROAD', name: 'Reading Railroad', group: 'RAILROAD', price: 200 },
  { index: 6, kind: 'PROPERTY', name: 'Oriental Avenue', group: 'LIGHT_BLUE', price: 100 },
  { index: 7, kind: 'CHANCE', name: 'Chance', group: null, price: null },
  { index: 8, kind: 'PROPERTY', name: 'Vermont Avenue', group: 'LIGHT_BLUE', price: 100 },
  { index: 9, kind: 'PROPERTY', name: 'Connecticut Avenue', group: 'LIGHT_BLUE', price: 120 },
  { index: 10, kind: 'JAIL', name: 'Jail', group: null, price: null },
  { index: 11, kind: 'PROPERTY', name: 'St. Charles Place', group: 'PINK', price: 140 },
  { index: 12, kind: 'UTILITY', name: 'Electric Company', group: 'UTILITY', price: 150 },
  { index: 13, kind: 'PROPERTY', name: 'States Avenue', group: 'PINK', price: 140 },
  { index: 14, kind: 'PROPERTY', name: 'Virginia Avenue', group: 'PINK', price: 160 },
  { index: 15, kind: 'RAILROAD', name: 'Pennsylvania Railroad', group: 'RAILROAD', price: 200 },
  { index: 16, kind: 'PROPERTY', name: 'St. James Place', group: 'ORANGE', price: 180 },
  { index: 17, kind: 'COMMUNITY_CHEST', name: 'Community Chest', group: null, price: null },
  { index: 18, kind: 'PROPERTY', name: 'Tennessee Avenue', group: 'ORANGE', price: 180 },
  { index: 19, kind: 'PROPERTY', name: 'New York Avenue', group: 'ORANGE', price: 200 },
  { index: 20, kind: 'FREE_PARKING', name: 'Free Parking', group: null, price: null },
  { index: 21, kind: 'PROPERTY', name: 'Kentucky Avenue', group: 'RED', price: 220 },
  { index: 22, kind: 'CHANCE', name: 'Chance', group: null, price: null },
  { index: 23, kind: 'PROPERTY', name: 'Indiana Avenue', group: 'RED', price: 220 },
  { index: 24, kind: 'PROPERTY', name: 'Illinois Avenue', group: 'RED', price: 240 },
  { index: 25, kind: 'RAILROAD', name: 'B. & O. Railroad', group: 'RAILROAD', price: 200 },
  { index: 26, kind: 'PROPERTY', name: 'Atlantic Avenue', group: 'YELLOW', price: 260 },
  { index: 27, kind: 'PROPERTY', name: 'Ventnor Avenue', group: 'YELLOW', price: 260 },
  { index: 28, kind: 'UTILITY', name: 'Water Works', group: 'UTILITY', price: 150 },
  { index: 29, kind: 'PROPERTY', name: 'Marvin Gardens', group: 'YELLOW', price: 280 },
  { index: 30, kind: 'GO_TO_JAIL', name: 'Go To Jail', group: null, price: null },
  { index: 31, kind: 'PROPERTY', name: 'Pacific Avenue', group: 'GREEN', price: 300 },
  { index: 32, kind: 'PROPERTY', name: 'North Carolina Avenue', group: 'GREEN', price: 300 },
  { index: 33, kind: 'COMMUNITY_CHEST', name: 'Community Chest', group: null, price: null },
  { index: 34, kind: 'PROPERTY', name: 'Pennsylvania Avenue', group: 'GREEN', price: 320 },
  { index: 35, kind: 'RAILROAD', name: 'Short Line', group: 'RAILROAD', price: 200 },
  { index: 36, kind: 'CHANCE', name: 'Chance', group: null, price: null },
  { index: 37, kind: 'PROPERTY', name: 'Park Place', group: 'DARK_BLUE', price: 350 },
  { index: 38, kind: 'TAX', name: 'Luxury Tax', group: null, price: null },
  { index: 39, kind: 'PROPERTY', name: 'Boardwalk', group: 'DARK_BLUE', price: 400 },
];

export const GROUP_ORDER: ReadonlyArray<GroupKey> = [
  'BROWN',
  'LIGHT_BLUE',
  'PINK',
  'ORANGE',
  'RED',
  'YELLOW',
  'GREEN',
  'DARK_BLUE',
];

export const SPECIAL_GROUP_ORDER: ReadonlyArray<GroupKey> = ['RAILROAD', 'UTILITY'];

export const GROUP_LABELS: Record<GroupKey, string> = {
  BROWN: 'Brown',
  LIGHT_BLUE: 'Light Blue',
  PINK: 'Pink',
  ORANGE: 'Orange',
  RED: 'Red',
  YELLOW: 'Yellow',
  GREEN: 'Green',
  DARK_BLUE: 'Dark Blue',
  RAILROAD: 'Railroads',
  UTILITY: 'Utilities',
};

export const BOARD_TILES_BY_INDEX: Record<number, BoardTile> = BOARD_TILES.reduce(
  (acc, tile) => {
    acc[tile.index] = tile;
    return acc;
  },
  {} as Record<number, BoardTile>
);

export const GROUP_TILE_INDEXES: Record<GroupKey, number[]> = BOARD_TILES.reduce(
  (acc, tile) => {
    if (tile.group) {
      acc[tile.group].push(tile.index);
    }
    return acc;
  },
  {
    BROWN: [],
    LIGHT_BLUE: [],
    PINK: [],
    ORANGE: [],
    RED: [],
    YELLOW: [],
    GREEN: [],
    DARK_BLUE: [],
    RAILROAD: [],
    UTILITY: [],
  } as Record<GroupKey, number[]>
);

export const normalizeGroupKey = (group: string | null | undefined): GroupKey | null => {
  if (!group) return null;
  const normalized = group.toUpperCase().replace(/\s+/g, '_');
  if (normalized in GROUP_LABELS) {
    return normalized as GroupKey;
  }
  return null;
};

export const getSpaceName = (index: number): string => {
  return BOARD_TILES_BY_INDEX[index]?.name ?? `Space ${index}`;
};

export const getGroupDisplayName = (group: GroupKey): string => {
  return GROUP_LABELS[group] ?? group;
};

export const GO_INDEX = 0;
export const JAIL_INDEX = 10;
export const FREE_PARKING_INDEX = 20;
export const GO_TO_JAIL_INDEX = 30;
