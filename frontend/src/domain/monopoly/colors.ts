import type { GroupKey } from '@/domain/monopoly/constants';
import { normalizeGroupKey } from '@/domain/monopoly/constants';

export const GROUP_COLORS: Record<GroupKey, string> = {
  BROWN: '#8B4513',
  LIGHT_BLUE: '#87CEEB',
  PINK: '#DB7093',
  ORANGE: '#FF8C00',
  RED: '#DC143C',
  YELLOW: '#FFD700',
  GREEN: '#228B22',
  DARK_BLUE: '#00008B',
  RAILROAD: '#1a1a1a',
  UTILITY: '#708090',
};

const PLAYER_COLOR_LIST = [
  '#ef4444',
  '#3b82f6',
  '#22c55e',
  '#eab308',
  '#a855f7',
  '#ec4899',
  '#f97316',
  '#64748b',
];

export const PLAYER_COLORS: Record<string, string> = {
  p1: PLAYER_COLOR_LIST[0],
  p2: PLAYER_COLOR_LIST[1],
  p3: PLAYER_COLOR_LIST[2],
  p4: PLAYER_COLOR_LIST[3],
  p5: PLAYER_COLOR_LIST[4],
  p6: PLAYER_COLOR_LIST[5],
  p7: PLAYER_COLOR_LIST[6],
  p8: PLAYER_COLOR_LIST[7],
  player_0: PLAYER_COLOR_LIST[0],
  player_1: PLAYER_COLOR_LIST[1],
  player_2: PLAYER_COLOR_LIST[2],
  player_3: PLAYER_COLOR_LIST[3],
  player_4: PLAYER_COLOR_LIST[4],
  player_5: PLAYER_COLOR_LIST[5],
  player_6: PLAYER_COLOR_LIST[6],
  player_7: PLAYER_COLOR_LIST[7],
};

export const getPlayerColor = (playerId: string): string => {
  if (PLAYER_COLORS[playerId]) return PLAYER_COLORS[playerId];
  let hash = 0;
  for (let i = 0; i < playerId.length; i += 1) {
    hash = playerId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return PLAYER_COLOR_LIST[Math.abs(hash) % PLAYER_COLOR_LIST.length];
};

export const getGroupColor = (group: GroupKey | string | null | undefined): string => {
  const key = typeof group === 'string' ? normalizeGroupKey(group) : group;
  if (!key) return 'transparent';
  return GROUP_COLORS[key] ?? 'transparent';
};

export const getPlayerIndex = (playerId: string): number => {
  if (/^p\d+$/.test(playerId)) {
    return Math.max(0, parseInt(playerId.slice(1), 10) - 1);
  }
  if (/^player_\d+$/.test(playerId)) {
    return Math.max(0, parseInt(playerId.split('_')[1], 10));
  }
  let hash = 0;
  for (let i = 0; i < playerId.length; i += 1) {
    hash = playerId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % PLAYER_COLOR_LIST.length;
};

export const getPlayerInitials = (playerId: string, name?: string | null): string => {
  if (name && name.trim().length > 0) {
    const trimmed = name.trim();
    const parts = trimmed.split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  if (playerId.startsWith('player_')) {
    return playerId.replace('player_', '').slice(0, 2).toUpperCase();
  }
  if (playerId.startsWith('p')) {
    return playerId.slice(1, 3).toUpperCase();
  }
  return playerId.slice(0, 2).toUpperCase();
};
