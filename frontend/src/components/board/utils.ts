export const getGridPosition = (index: number) => {
    if (index >= 0 && index <= 10) {
        // Bottom: 0 is at 11/11. 10 is at 11/1.
        return { row: 11, col: 11 - index };
    } else if (index >= 11 && index <= 19) {
        // Left: 11 is at 10/1. 19 is at 2/1.
        return { row: 11 - (index - 10), col: 1 };
    } else if (index >= 20 && index <= 30) {
        // Top: 20 is at 1/1. 30 is at 1/11.
        return { row: 1, col: 1 + (index - 20) };
    } else {
        // Right: 31 is at 2/11. 39 is at 10/11.
        return { row: 1 + (index - 30), col: 11 };
    }
};

// Start at bottom right, clockwise
export const getCSSPosition = (index: number) => {
    const { row, col } = getGridPosition(index);
    // Convert 1-based grid coordinates to percentages
    // Grid is 11x11.
    // center x = (col - 0.5) / 11 * 100
    // center y = (row - 0.5) / 11 * 100
    const x = ((col - 0.5) / 11) * 100;
    const y = ((row - 0.5) / 11) * 100;
    return { x, y };
}
