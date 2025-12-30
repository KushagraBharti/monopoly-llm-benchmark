import { formatCardTitle } from '@/domain/monopoly/formatters';

export interface CardDefinition {
  title: string;
  description: string;
}

const CARD_DESCRIPTIONS: Record<string, string> = {
  ADVANCE_TO_GO: 'Advance to Go. Collect $200.',
  GO_TO_ILLINOIS_AVE: 'Advance to Illinois Avenue. If you pass Go, collect $200.',
  GO_TO_ST_CHARLES_PLACE: 'Advance to St. Charles Place. If you pass Go, collect $200.',
  GO_TO_NEAREST_UTILITY: 'Advance to the nearest Utility. If unowned, you may buy it; if owned, pay rent.',
  GO_TO_NEAREST_RAILROAD: 'Advance to the nearest Railroad. If unowned, you may buy it; if owned, pay rent.',
  BANK_PAYS_YOU_DIVIDEND_50: 'Bank pays you $50.',
  GET_OUT_OF_JAIL_FREE: 'Get Out of Jail Free. Keep until needed or trade.',
  GO_BACK_3_SPACES: 'Go back 3 spaces.',
  GO_TO_JAIL: 'Go directly to Jail. Do not pass Go; do not collect $200.',
  GENERAL_REPAIRS: 'Pay $25 per house and $100 per hotel.',
  PAY_POOR_TAX_15: 'Pay poor tax of $15.',
  TAKE_TRIP_TO_READING_RR: 'Take a trip to Reading Railroad. If you pass Go, collect $200.',
  ADVANCE_TO_BOARDWALK: 'Advance to Boardwalk.',
  ELECTED_CHAIRMAN_PAY_EACH_PLAYER_50: 'Pay each player $50.',
  BUILDING_LOAN_MATURES_RECEIVE_150: 'Collect $150.',
  BANK_ERROR_COLLECT_200: 'Collect $200.',
  DOCTOR_FEE_PAY_50: 'Pay $50.',
  SALE_OF_STOCK_COLLECT_50: 'Collect $50.',
  HOLIDAY_FUND_RECEIVE_100: 'Collect $100.',
  INCOME_TAX_REFUND_COLLECT_20: 'Collect $20.',
  BIRTHDAY_COLLECT_10_FROM_EACH_PLAYER: 'Collect $10 from each player.',
  LIFE_INSURANCE_COLLECT_100: 'Collect $100.',
  HOSPITAL_FEES_PAY_100: 'Pay $100.',
  SCHOOL_FEES_PAY_50: 'Pay $50.',
  CONSULTANCY_FEE_COLLECT_25: 'Collect $25.',
  STREET_REPAIRS: 'Pay $40 per house and $115 per hotel.',
  BEAUTY_CONTEST_COLLECT_10: 'Collect $10.',
  INHERIT_100: 'Collect $100.',
};

const normalizeCardId = (cardId: string): string => {
  const normalized = cardId.trim().replace(/[^A-Za-z0-9]+/g, '_').toUpperCase();
  if (normalized === 'GO_TO_NEAREST_RAILROAD_A' || normalized === 'GO_TO_NEAREST_RAILROAD_B') {
    return 'GO_TO_NEAREST_RAILROAD';
  }
  return normalized;
};

export const getCardDetails = (
  deck: 'CHANCE' | 'COMMUNITY_CHEST',
  cardId: string
): CardDefinition => {
  const normalized = normalizeCardId(cardId);
  const title = formatCardTitle(normalized);
  const deckLabel = deck === 'CHANCE' ? 'Chance' : 'Community Chest';
  const description = CARD_DESCRIPTIONS[normalized] ?? `${deckLabel} card: ${title}.`;

  return {
    title,
    description,
  };
};
