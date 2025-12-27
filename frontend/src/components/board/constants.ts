/**
 * Monopoly board constants - Color mappings for property groups and players.
 * Group keys MUST match backend format: uppercase with underscores.
 */

// Property group colors - keys match backend BOARD_SPEC exactly
export const GROUP_COLORS: Record<string, string> = {
    // Standard property groups (official Monopoly colors)
    BROWN: "#8B4513",
    LIGHT_BLUE: "#87CEEB",
    PINK: "#DB7093", // Slightly adjusted for better visibility
    ORANGE: "#FF8C00",
    RED: "#DC143C",
    YELLOW: "#FFD700",
    GREEN: "#228B22",
    DARK_BLUE: "#00008B",
    // Non-property groups
    RAILROAD: "#1a1a1a",
    UTILITY: "#708090",
};

// Player token colors - up to 8 players
export const PLAYER_COLORS: Record<string, string> = {
    "p1": "#ef4444", // Red-500
    "p2": "#3b82f6", // Blue-500
    "p3": "#22c55e", // Green-500
    "p4": "#eab308", // Yellow-500
    "p5": "#a855f7", // Purple-500
    "p6": "#ec4899", // Pink-500
    "p7": "#f97316", // Orange-500
    "p8": "#64748b", // Slate-500
    // Legacy format support
    "player_0": "#ef4444",
    "player_1": "#3b82f6",
    "player_2": "#22c55e",
    "player_3": "#eab308",
    "player_4": "#a855f7",
    "player_5": "#ec4899",
    "player_6": "#f97316",
    "player_7": "#64748b",
};

/**
 * Get consistent color for a player ID.
 * Falls back to hash-based selection for unknown IDs.
 */
export const getPlayerColor = (playerId: string): string => {
    // Direct match
    if (PLAYER_COLORS[playerId]) return PLAYER_COLORS[playerId];

    // Hash-based fallback for arbitrary player IDs
    const colors = Object.values(PLAYER_COLORS).slice(0, 8);
    let hash = 0;
    for (let i = 0; i < playerId.length; i++) {
        hash = playerId.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
};

/**
 * Get group color with case-insensitive lookup for safety.
 */
export const getGroupColor = (group: string | null): string => {
    if (!group) return 'transparent';

    // Try exact match first
    if (GROUP_COLORS[group]) return GROUP_COLORS[group];

    // Try uppercase match (backend format)
    const upper = group.toUpperCase().replace(/\s+/g, '_');
    if (GROUP_COLORS[upper]) return GROUP_COLORS[upper];

    return 'transparent';
};

// Player index for ordering calculations
export const getPlayerIndex = (playerId: string): number => {
    // Handle p1, p2, etc.
    if (/^p\d+$/.test(playerId)) {
        return parseInt(playerId.slice(1), 10) - 1;
    }
    // Handle player_0, player_1, etc.
    if (/^player_\d+$/.test(playerId)) {
        return parseInt(playerId.split('_')[1], 10);
    }
    // Hash fallback
    let hash = 0;
    for (let i = 0; i < playerId.length; i++) {
        hash = playerId.charCodeAt(i) + ((hash << 5) - hash);
    }
    return Math.abs(hash) % 8;
};
