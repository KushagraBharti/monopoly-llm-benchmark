import type { Space } from '@/net/contracts';
import boardSpecJson from '@contracts-data/board.json';

type SpaceKind = Space['kind'];

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

type BoardSpec = {
  schema_version: 'v1';
  spaces: ReadonlyArray<BoardTile>;
};

const BOARD_SPEC = boardSpecJson as unknown as BoardSpec;

export const BOARD_TILES: ReadonlyArray<BoardTile> = BOARD_SPEC.spaces;

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
