export const GROUP_COLORS: Record<string, string> = {
    Brown: "#8B4513",
    LightBlue: "#87CEEB",
    Pink: "#FF69B4",
    Orange: "#FFA500",
    Red: "#FF0000",
    Yellow: "#FFD700",
    Green: "#008000",
    Blue: "#0000FF",
    Railroad: "#000000", // Classic black for RR
    Utility: "#a4b0be",
};

export const PLAYER_COLORS: Record<string, string> = {
    // Deterministic mapping for up to 8 players reasonably
    "player_0": "#ef4444", // Red-500
    "player_1": "#3b82f6", // Blue-500
    "player_2": "#22c55e", // Green-500
    "player_3": "#eab308", // Yellow-500
    "player_4": "#a855f7", // Purple-500
    "player_5": "#ec4899", // Pink-500
    "player_6": "#f97316", // Orange-500
    "player_7": "#64748b", // Slate-500
};

export const getPlayerColor = (playerId: string) => {
    // If exact match
    if (PLAYER_COLORS[playerId]) return PLAYER_COLORS[playerId];

    // Hash backup
    const colors = Object.values(PLAYER_COLORS);
    let hash = 0;
    for (let i = 0; i < playerId.length; i++) {
        hash = playerId.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
};
