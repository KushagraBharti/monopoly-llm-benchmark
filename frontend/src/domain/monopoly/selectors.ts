import type { Event, Space, StateSnapshot } from '../../net/contracts';
import type { GroupKey } from './constants';
import {
  GROUP_ORDER,
  SPECIAL_GROUP_ORDER,
  getGroupDisplayName,
  normalizeGroupKey,
} from './constants';
import { getGroupColor } from './colors';

export type OwnershipGroup = {
  key: GroupKey;
  label: string;
  color: string;
  tiles: Space[];
  totalCount: number;
  ownedCount: number;
  ownedByPlayerCount?: number;
  monopolyOwnerId: string | null;
  isComplete: boolean;
};

const groupSortOrder = [...GROUP_ORDER, ...SPECIAL_GROUP_ORDER];

export const selectOwnershipGroups = (
  snapshot: StateSnapshot | null,
  filterPlayerId: string | null = null
): OwnershipGroup[] => {
  if (!snapshot) return [];
  const board = snapshot.board ?? [];

  const grouped = new Map<GroupKey, Space[]>();
  board.forEach((space) => {
    const key = normalizeGroupKey(space.group);
    if (!key) return;
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key)?.push(space);
  });

  return groupSortOrder
    .map((key) => {
      const groupTiles = (grouped.get(key) ?? []).sort((a, b) => a.index - b.index);
      const ownedTiles = groupTiles.filter((tile) => tile.owner_id);
      const ownedByPlayer = filterPlayerId
        ? groupTiles.filter((tile) => tile.owner_id === filterPlayerId)
        : [];
      const visibleTiles = filterPlayerId ? ownedByPlayer : groupTiles;

      const ownerIds = groupTiles.map((tile) => tile.owner_id).filter(Boolean) as string[];
      const monopolyOwnerId =
        ownerIds.length === groupTiles.length && new Set(ownerIds).size === 1
          ? ownerIds[0]
          : null;

      return {
        key,
        label: getGroupDisplayName(key),
        color: getGroupColor(key),
        tiles: visibleTiles,
        totalCount: groupTiles.length,
        ownedCount: ownedTiles.length,
        ownedByPlayerCount: filterPlayerId ? ownedByPlayer.length : undefined,
        monopolyOwnerId,
        isComplete: monopolyOwnerId !== null,
      };
    })
    .filter((group) => group.tiles.length > 0 || !filterPlayerId);
};

export const selectPropertiesByPlayer = (
  snapshot: StateSnapshot | null
): Record<string, Space[]> => {
  const map: Record<string, Space[]> = {};
  if (!snapshot) return map;
  snapshot.players.forEach((player) => {
    map[player.player_id] = [];
  });
  snapshot.board.forEach((space) => {
    if (!space.owner_id) return;
    if (!map[space.owner_id]) {
      map[space.owner_id] = [];
    }
    map[space.owner_id].push(space);
  });
  return map;
};

export type PlayerStanding = {
  player_id: string;
  name: string;
  cash: number;
  netWorthEstimate: number;
  propertyCount: number;
  inJail: boolean;
  bankrupt: boolean;
};

export const selectLeaderboard = (snapshot: StateSnapshot | null): PlayerStanding[] => {
  if (!snapshot) return [];
  const derivedNetWorth = snapshot.derived?.net_worth_estimate_by_player ?? {};
  const propertyMap = selectPropertiesByPlayer(snapshot);

  return snapshot.players.map((player) => {
    const properties = propertyMap[player.player_id] ?? [];
    const fallbackPropertyValue = properties.reduce((sum, space) => sum + (space.price ?? 0), 0);
    const netWorthEstimate = derivedNetWorth[player.player_id] ?? player.cash + fallbackPropertyValue;
    return {
      player_id: player.player_id,
      name: player.name,
      cash: player.cash,
      netWorthEstimate,
      propertyCount: properties.length,
      inJail: player.in_jail,
      bankrupt: player.bankrupt,
    };
  });
};

export const selectLandingHeatmap = (events: Event[], limit = 200): number[] => {
  const counts = Array.from({ length: 40 }).fill(0) as number[];
  events.slice(0, limit).forEach((event) => {
    if (event.type === 'PLAYER_MOVED') {
      counts[event.payload.to] += 1;
    }
  });
  return counts;
};

export const selectSpaceByIndex = (
  snapshot: StateSnapshot | null,
  index: number
): Space | null => {
  if (!snapshot) return null;
  return snapshot.board.find((space) => space.index === index) ?? null;
};
