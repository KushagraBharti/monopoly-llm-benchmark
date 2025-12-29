export interface CardDefinition {
    title: string;
    description: string;
}

export const CHANCE_CARDS: Record<string, CardDefinition> = {
    // Classic Chance
    "advance_to_go": { title: "Advance to Go", description: "Advance to Google (Go). Collect $200." },
    "avenue_illinois": { title: "Advance to Illinois Ave", description: "Advance to Illinois Avenue. If you pass Go, collect $200." },
    "utility_nearest": { title: "Advance to Utility", description: "Advance token to nearest Utility. If unowned, you may buy it." },
    "railroad_nearest": { title: "Advance to Railroad", description: "Advance to nearest Railroad. If unowned, you may buy it." },
    "avenue_st_charles": { title: "Advance to St. Charles", description: "Advance to St. Charles Place. If you pass Go, collect $200." },
    "dividend_bank": { title: "Bank Dividend", description: "Bank pays you dividend of $50." },
    "get_out_of_jail": { title: "Get Out of Jail", description: "Get Out of Jail Free. This card may be kept until needed or sold." },
    "go_back_3": { title: "Go Back 3 Spaces", description: "Go back 3 spaces." },
    "jail_go_directly": { title: "Go to Jail", description: "Go directly to Jail. Do not pass Go, do not collect $200." },
    "repairs_general": { title: "General Repairs", description: "Make general repairs on all your property. For each house pay $25, for each hotel pay $100." },
    "poor_tax": { title: "Poor Tax", description: "Speeding fine. Pay $15." },
    "trip_reading": { title: "Take a Trip", description: "Take a trip to Reading Railroad. If you pass Go, collect $200." },
    "walk_boardwalk": { title: "Walk on Boardwalk", description: "Advance token to Boardwalk." },
    "chairman_elected": { title: "Elected Chairman", description: "You have been elected Chairman of the Board. Pay each player $50." },
    "building_loan": { title: "Building Loan", description: "Your building loan matures. Collect $150." },

    // Add fallbacks for generic IDs if the engine uses IDs like "chance_0", "chance_1" etc.
    // Ideally the engine should send stable string IDs. If not, we might need a fallback.
};

export const COMMUNITY_CHEST_CARDS: Record<string, CardDefinition> = {
    "advance_to_go": { title: "Advance to Go", description: "Advance to Google (Go). Collect $200." },
    "bank_error": { title: "Bank Error", description: "Bank error in your favor. Collect $200." },
    "doctor_fee": { title: "Doctor's Fee", description: "Doctor's fee. Pay $50." },
    "stock_sale": { title: "Stock Sale", description: "From sale of stock you get $50." },
    "get_out_of_jail": { title: "Get Out of Jail", description: "Get Out of Jail Free. This card may be kept until needed or sold." },
    "jail_go_directly": { title: "Go to Jail", description: "Go directly to Jail. Do not pass Go, do not collect $200." },
    "opera_night": { title: "Grand Opera", description: "Grand Opera Night. Collect $50 from every player for opening night seats." },
    "holiday_fund": { title: "Xmas Fund", description: "Holiday Fund matures. Receive $100." },
    "tax_refund": { title: "Tax Refund", description: "Income tax refund. Collect $20." },
    "birthday": { title: "Birthday", description: "It is your birthday. Collect $10 from every player." },
    "insurance_mature": { title: "Life Insurance", description: "Life insurance matures. Collect $100." },
    "hospital_fee": { title: "Hospital Fees", description: "Pay hospital fees of $100." },
    "school_tax": { title: "School Tax", description: "Pay school tax of $150." },
    "consultancy_fee": { title: "Consultancy Fee", description: "Receive $25 consultancy fee." },
    "street_repair": { title: "Street Repairs", description: "You are assessed for street repairs. $40 per house, $115 per hotel." },
    "beauty_contest": { title: "Beauty Contest", description: "You have won second prize in a beauty contest. Collect $10." },
    "inherit": { title: "Inheritance", description: "You inherit $100." },
};

export const getCardDetails = (deck: 'CHANCE' | 'COMMUNITY_CHEST', cardId: string): CardDefinition => {
    const collection = deck === 'CHANCE' ? CHANCE_CARDS : COMMUNITY_CHEST_CARDS;

    // Direct match
    if (collection[cardId]) {
        return collection[cardId];
    }

    // Try some heuristics or fallback
    // e.g. "CC_01" might map to index

    return {
        title: deck === 'CHANCE' ? "Chance" : "Community Chest",
        description: `Card #${cardId}`
    };
};
