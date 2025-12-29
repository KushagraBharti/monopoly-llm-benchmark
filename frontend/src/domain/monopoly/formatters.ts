import type { Event } from '@/net/contracts';
import { getSpaceName, SPACE_INDEX_BY_KEY } from '@/domain/monopoly/constants';

export type EventSeverity = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type EventBadge = {
  text: string;
  tone?: EventSeverity;
};

export type EventCardPart =
  | { kind: 'text'; value: string }
  | { kind: 'player'; playerId: string }
  | { kind: 'money'; amount: number; showSign?: boolean }
  | { kind: 'space'; spaceIndex: number };

export type EventCard = {
  id: string;
  type: Event['type'];
  turnIndex: number;
  icon: string;
  title: string;
  severity: EventSeverity;
  parts: EventCardPart[];
  badges: EventBadge[];
  isMinor?: boolean;
  details: Record<string, unknown>;
  highlightSpaceIndices?: number[];
};

export const formatMoney = (amount: number, showSign = false): string => {
  const sign = showSign ? (amount >= 0 ? '+' : '-') : '';
  return `${sign}$${Math.abs(amount)}`;
};

const formatSpaceKey = (spaceKey: string): string => {
  const spaceIndex = SPACE_INDEX_BY_KEY[spaceKey];
  return spaceIndex !== undefined ? getSpaceName(spaceIndex) : spaceKey;
};

const formatTradeBundle = (bundle: {
  cash?: number;
  properties?: string[];
  get_out_of_jail_cards?: number;
}): string => {
  const parts: string[] = [];
  if (bundle.cash) {
    parts.push(formatMoney(bundle.cash));
  }
  const properties = bundle.properties ?? [];
  if (properties.length) {
    parts.push(properties.map(formatSpaceKey).join(', '));
  }
  if (bundle.get_out_of_jail_cards) {
    parts.push(`${bundle.get_out_of_jail_cards} jail card`);
  }
  return parts.length ? parts.join(' + ') : 'nothing';
};

const formatCount = (count: number, label: string): string => {
  return `${count} ${label}${count === 1 ? '' : 's'}`;
};

const CARD_TITLES: Record<string, string> = {
  ADVANCE_TO_GO: 'Advance to Go',
  GO_TO_ILLINOIS_AVE: 'Go to Illinois Avenue',
  GO_TO_ST_CHARLES_PLACE: 'Go to St. Charles Place',
  GO_TO_NEAREST_UTILITY: 'Go to Nearest Utility',
  GO_TO_NEAREST_RAILROAD_A: 'Go to Nearest Railroad',
  GO_TO_NEAREST_RAILROAD_B: 'Go to Nearest Railroad',
  BANK_PAYS_YOU_DIVIDEND_50: 'Bank Pays You $50',
  GET_OUT_OF_JAIL_FREE: 'Get Out of Jail Free',
  GO_BACK_3_SPACES: 'Go Back 3 Spaces',
  GO_TO_JAIL: 'Go to Jail',
  GENERAL_REPAIRS: 'General Repairs',
  PAY_POOR_TAX_15: 'Pay Poor Tax $15',
  TAKE_TRIP_TO_READING_RR: 'Take a Trip to Reading Railroad',
  ADVANCE_TO_BOARDWALK: 'Advance to Boardwalk',
  ELECTED_CHAIRMAN_PAY_EACH_PLAYER_50: 'Elected Chairman (Pay $50 Each)',
  BUILDING_LOAN_MATURES_RECEIVE_150: 'Building Loan Matures (Collect $150)',
  BANK_ERROR_COLLECT_200: 'Bank Error in Your Favor (Collect $200)',
  DOCTOR_FEE_PAY_50: "Doctor's Fee (Pay $50)",
  SALE_OF_STOCK_COLLECT_50: 'Sale of Stock (Collect $50)',
  HOLIDAY_FUND_RECEIVE_100: 'Holiday Fund Matures (Collect $100)',
  INCOME_TAX_REFUND_COLLECT_20: 'Income Tax Refund (Collect $20)',
  BIRTHDAY_COLLECT_10_FROM_EACH_PLAYER: 'Birthday (Collect $10 Each)',
  LIFE_INSURANCE_COLLECT_100: 'Life Insurance (Collect $100)',
  HOSPITAL_FEES_PAY_100: 'Hospital Fees (Pay $100)',
  SCHOOL_FEES_PAY_50: 'School Fees (Pay $50)',
  CONSULTANCY_FEE_COLLECT_25: 'Consultancy Fee (Collect $25)',
  STREET_REPAIRS: 'Street Repairs',
  BEAUTY_CONTEST_COLLECT_10: 'Beauty Contest (Collect $10)',
  INHERIT_100: 'Inherit $100',
};

export const formatCardTitle = (cardId: string): string => {
  return CARD_TITLES[cardId] ?? cardId.replace(/_/g, ' ');
};

const defaultCard = (event: Event): EventCard => ({
  id: event.event_id,
  type: event.type,
  turnIndex: event.turn_index,
  icon: '??',
  title: event.type.replace(/_/g, ' '),
  severity: 'neutral',
  parts: [{ kind: 'text', value: 'Unhandled event.' }],
  badges: [],
  isMinor: true,
  details: event as unknown as Record<string, unknown>,
});

const resolveSpaceIndex = (spaceKey?: string | null): number | null => {
  if (!spaceKey) return null;
  const normalized = spaceKey.toUpperCase();
  return SPACE_INDEX_BY_KEY[normalized] ?? null;
};

export const formatEventCard = (event: Event): EventCard => {
  const base = {
    id: event.event_id,
    type: event.type,
    turnIndex: event.turn_index,
    details: event as unknown as Record<string, unknown>,
  };

  switch (event.type) {
    case 'GAME_STARTED':
      return {
        ...base,
        icon: '>>',
        title: 'Game Started',
        severity: 'info',
        parts: [{ kind: 'text', value: 'The game is on.' }],
        badges: [],
      };
    case 'GAME_ENDED':
      return {
        ...base,
        icon: '!!',
        title: 'Game Over',
        severity: 'success',
        parts: [
          { kind: 'text', value: 'Winner:' },
          { kind: 'player', playerId: event.payload.winner_player_id },
        ],
        badges: [{ text: event.payload.reason, tone: 'warning' }],
      };
    case 'TURN_STARTED':
      return {
        ...base,
        icon: '>>',
        title: 'Turn Started',
        severity: 'info',
        parts: [{ kind: 'text', value: 'New turn begins.' }],
        badges: [],
      };
    case 'TURN_ENDED':
      return {
        ...base,
        icon: '--',
        title: 'Turn Ended',
        severity: 'neutral',
        parts: [{ kind: 'text', value: 'Turn closed out.' }],
        badges: [],
        isMinor: true,
      };
    case 'DICE_ROLLED': {
      const total = event.payload.d1 + event.payload.d2;
      const badges: EventBadge[] = [];
      if (event.payload.is_double) {
        badges.push({ text: 'DOUBLE', tone: 'warning' });
      }
      if (event.payload.reason) {
        badges.push({ text: event.payload.reason.replace(/_/g, ' '), tone: 'info' });
      }
      return {
        ...base,
        icon: 'D6',
        title: 'Dice Rolled',
        severity: 'neutral',
        parts: [{ kind: 'text', value: `Rolled ${event.payload.d1} + ${event.payload.d2} = ${total}` }],
        badges,
      };
    }
    case 'PLAYER_MOVED': {
      const badges: EventBadge[] = [];
      if (event.payload.passed_go) {
        badges.push({ text: 'PASSED GO', tone: 'success' });
      }
      return {
        ...base,
        icon: '->',
        title: 'Player Moved',
        severity: 'info',
        parts: [
          { kind: 'text', value: 'Moved' },
          { kind: 'space', spaceIndex: event.payload.from },
          { kind: 'text', value: 'to' },
          { kind: 'space', spaceIndex: event.payload.to },
        ],
        badges,
        highlightSpaceIndices: [event.payload.to],
      };
    }
    case 'PROPERTY_PURCHASED':
      return {
        ...base,
        icon: '$$',
        title: 'Property Purchased',
        severity: 'success',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'bought' },
          { kind: 'space', spaceIndex: event.payload.space_index },
          { kind: 'text', value: 'for' },
          { kind: 'money', amount: event.payload.price },
        ],
        badges: [],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'RENT_PAID':
      return {
        ...base,
        icon: '-$',
        title: 'Rent Paid',
        severity: 'danger',
        parts: [
          { kind: 'player', playerId: event.payload.from_player_id },
          { kind: 'text', value: 'paid' },
          { kind: 'money', amount: event.payload.amount },
          { kind: 'text', value: 'to' },
          { kind: 'player', playerId: event.payload.to_player_id },
          { kind: 'text', value: 'for' },
          { kind: 'space', spaceIndex: event.payload.space_index },
        ],
        badges: [{ text: 'RENT', tone: 'danger' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'CASH_CHANGED':
      return {
        ...base,
        icon: event.payload.delta >= 0 ? '+$' : '-$',
        title: 'Cash Change',
        severity: event.payload.delta >= 0 ? 'success' : 'danger',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'money', amount: event.payload.delta, showSign: true },
          { kind: 'text', value: `(${event.payload.reason})` },
        ],
        badges: [],
        isMinor: true,
      };
    case 'SENT_TO_JAIL':
      return {
        ...base,
        icon: 'J!',
        title: 'Sent To Jail',
        severity: 'warning',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'sent to jail' },
          { kind: 'text', value: `(${event.payload.reason})` },
        ],
        badges: [{ text: 'JAIL', tone: 'warning' }],
      };
    case 'CARD_DRAWN': {
      const deckLabel = event.payload.deck_type === 'CHANCE' ? 'Chance' : 'Community Chest';
      const cardTitle = formatCardTitle(event.payload.card_id);
      return {
        ...base,
        icon: '[]',
        title: 'Card Drawn',
        severity: 'info',
        parts: [
          { kind: 'player', playerId: event.actor.player_id ?? 'unknown' },
          { kind: 'text', value: 'drew' },
          { kind: 'text', value: deckLabel },
          { kind: 'text', value: 'card:' },
          { kind: 'text', value: cardTitle },
        ],
        badges: [{ text: deckLabel.toUpperCase(), tone: 'info' }],
      };
    }
    case 'HOUSE_BUILT':
      return {
        ...base,
        icon: 'H+',
        title: 'House Built',
        severity: 'success',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'built' },
          { kind: 'text', value: formatCount(event.payload.count, 'house') },
          { kind: 'text', value: 'on' },
          { kind: 'space', spaceIndex: event.payload.space_index },
        ],
        badges: [{ text: 'BUILD', tone: 'success' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'AUCTION_STARTED': {
      const spaceIndex = resolveSpaceIndex(event.payload.property_space);
      return {
        ...base,
        icon: 'A+',
        title: 'Auction Started',
        severity: 'info',
        parts: [
          { kind: 'text', value: 'Auction for' },
          ...(spaceIndex !== null
            ? [{ kind: 'space', spaceIndex } as const]
            : [{ kind: 'text', value: event.payload.property_space } as const]),
          { kind: 'text', value: 'started by' },
          { kind: 'player', playerId: event.payload.initiator_player_id },
        ],
        badges: [{ text: 'AUCTION', tone: 'info' }],
        highlightSpaceIndices: spaceIndex !== null ? [spaceIndex] : undefined,
      };
    }
    case 'AUCTION_BID_PLACED': {
      const spaceIndex = resolveSpaceIndex(event.payload.property_space);
      return {
        ...base,
        icon: 'A$',
        title: 'Auction Bid',
        severity: 'info',
        parts: [
          { kind: 'player', playerId: event.payload.bidder_player_id },
          { kind: 'text', value: 'bid' },
          { kind: 'money', amount: event.payload.bid_amount },
          { kind: 'text', value: 'on' },
          ...(spaceIndex !== null
            ? [{ kind: 'space', spaceIndex } as const]
            : [{ kind: 'text', value: event.payload.property_space } as const]),
        ],
        badges: [{ text: 'BID', tone: 'info' }],
        highlightSpaceIndices: spaceIndex !== null ? [spaceIndex] : undefined,
      };
    }
    case 'AUCTION_PLAYER_DROPPED': {
      const spaceIndex = resolveSpaceIndex(event.payload.property_space);
      return {
        ...base,
        icon: 'A-',
        title: 'Auction Drop Out',
        severity: 'warning',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'dropped out of' },
          ...(spaceIndex !== null
            ? [{ kind: 'space', spaceIndex } as const]
            : [{ kind: 'text', value: event.payload.property_space } as const]),
        ],
        badges: [{ text: 'AUCTION', tone: 'warning' }],
        highlightSpaceIndices: spaceIndex !== null ? [spaceIndex] : undefined,
      };
    }
    case 'AUCTION_ENDED': {
      const spaceIndex = resolveSpaceIndex(event.payload.property_space);
      const sold = event.payload.reason === 'SOLD';
      const parts: EventCardPart[] = [
        { kind: 'text', value: 'Auction ended for' },
        ...(spaceIndex !== null
          ? [{ kind: 'space', spaceIndex } as const]
          : [{ kind: 'text', value: event.payload.property_space } as const]),
      ];
      if (sold && event.payload.winner_player_id) {
        parts.push({ kind: 'text', value: 'won by' });
        parts.push({ kind: 'player', playerId: event.payload.winner_player_id });
        if (typeof event.payload.winning_bid === 'number') {
          parts.push({ kind: 'text', value: 'for' });
          parts.push({ kind: 'money', amount: event.payload.winning_bid });
        }
      } else {
        parts.push({ kind: 'text', value: '(no bids)' });
      }
      return {
        ...base,
        icon: 'A*',
        title: 'Auction Ended',
        severity: sold ? 'success' : 'neutral',
        parts,
        badges: [{ text: event.payload.reason, tone: sold ? 'success' : 'neutral' }],
        highlightSpaceIndices: spaceIndex !== null ? [spaceIndex] : undefined,
      };
    }
    case 'TRADE_PROPOSED':
      return {
        ...base,
        icon: 'T+',
        title: 'Trade Proposed',
        severity: 'info',
        parts: [
          { kind: 'player', playerId: event.payload.initiator_player_id },
          { kind: 'text', value: 'proposed trade with' },
          { kind: 'player', playerId: event.payload.counterparty_player_id },
          { kind: 'text', value: `Offer: ${formatTradeBundle(event.payload.offer)}` },
          { kind: 'text', value: `Request: ${formatTradeBundle(event.payload.request)}` },
        ],
        badges: [
          {
            text: `${event.payload.exchange_index}/${event.payload.max_exchanges}`,
            tone: 'info',
          },
        ],
      };
    case 'TRADE_COUNTERED':
      return {
        ...base,
        icon: 'T~',
        title: 'Trade Countered',
        severity: 'info',
        parts: [
          { kind: 'player', playerId: event.actor.player_id ?? event.payload.initiator_player_id },
          { kind: 'text', value: 'countered the trade' },
          { kind: 'text', value: `Offer: ${formatTradeBundle(event.payload.offer)}` },
          { kind: 'text', value: `Request: ${formatTradeBundle(event.payload.request)}` },
        ],
        badges: [
          {
            text: `${event.payload.exchange_index}/${event.payload.max_exchanges}`,
            tone: 'info',
          },
        ],
      };
    case 'TRADE_ACCEPTED':
      return {
        ...base,
        icon: 'T=',
        title: 'Trade Accepted',
        severity: 'success',
        parts: [
          { kind: 'player', playerId: event.actor.player_id ?? event.payload.counterparty_player_id },
          { kind: 'text', value: 'accepted the trade' },
          { kind: 'text', value: `Offer: ${formatTradeBundle(event.payload.offer)}` },
          { kind: 'text', value: `Request: ${formatTradeBundle(event.payload.request)}` },
        ],
        badges: [{ text: 'ACCEPTED', tone: 'success' }],
      };
    case 'TRADE_REJECTED':
      return {
        ...base,
        icon: 'T-',
        title: 'Trade Rejected',
        severity: 'warning',
        parts: [
          { kind: 'player', playerId: event.actor.player_id ?? event.payload.counterparty_player_id },
          { kind: 'text', value: 'rejected the trade' },
        ],
        badges: [{ text: 'REJECTED', tone: 'warning' }],
      };
    case 'TRADE_EXPIRED':
      return {
        ...base,
        icon: 'T!',
        title: 'Trade Expired',
        severity: 'neutral',
        parts: [
          { kind: 'text', value: 'Trade expired between' },
          { kind: 'player', playerId: event.payload.initiator_player_id },
          { kind: 'text', value: 'and' },
          { kind: 'player', playerId: event.payload.counterparty_player_id },
        ],
        badges: [{ text: event.payload.reason ?? 'EXPIRED', tone: 'neutral' }],
      };
    case 'PROPERTY_TRANSFERRED':
      {
        const fromPlayer = event.payload.from_player_id;
        const toPlayer = event.payload.to_player_id;
        const parts: EventCardPart[] = [
          { kind: 'text', value: 'Property' },
          { kind: 'space', spaceIndex: event.payload.space_index },
          { kind: 'text', value: 'moved from' },
          ...(fromPlayer
            ? [{ kind: 'player', playerId: fromPlayer } as const]
            : [{ kind: 'text', value: 'Bank' } as const]),
          { kind: 'text', value: 'to' },
          ...(toPlayer
            ? [{ kind: 'player', playerId: toPlayer } as const]
            : [{ kind: 'text', value: 'Bank' } as const]),
        ];
        return {
          ...base,
          icon: 'T>',
          title: 'Property Transferred',
          severity: 'info',
          parts,
          badges: [
            { text: event.payload.mortgaged ? 'MORTGAGED' : 'UNMORTGAGED', tone: 'info' },
          ],
          highlightSpaceIndices: [event.payload.space_index],
        };
      }
    case 'HOTEL_BUILT':
      return {
        ...base,
        icon: 'H*',
        title: 'Hotel Built',
        severity: 'success',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'built' },
          { kind: 'text', value: formatCount(event.payload.count, 'hotel') },
          { kind: 'text', value: 'on' },
          { kind: 'space', spaceIndex: event.payload.space_index },
        ],
        badges: [{ text: 'BUILD', tone: 'success' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'HOUSE_SOLD':
      return {
        ...base,
        icon: 'H-',
        title: 'House Sold',
        severity: 'warning',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'sold' },
          { kind: 'text', value: formatCount(event.payload.count, 'house') },
          { kind: 'text', value: 'from' },
          { kind: 'space', spaceIndex: event.payload.space_index },
        ],
        badges: [{ text: 'SELL', tone: 'warning' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'HOTEL_SOLD':
      return {
        ...base,
        icon: 'H!',
        title: 'Hotel Sold',
        severity: 'warning',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'sold' },
          { kind: 'text', value: formatCount(event.payload.count, 'hotel') },
          { kind: 'text', value: 'from' },
          { kind: 'space', spaceIndex: event.payload.space_index },
        ],
        badges: [{ text: 'SELL', tone: 'warning' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'PROPERTY_MORTGAGED':
      return {
        ...base,
        icon: 'M$',
        title: 'Property Mortgaged',
        severity: 'warning',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'mortgaged' },
          { kind: 'space', spaceIndex: event.payload.space_index },
          { kind: 'text', value: 'for' },
          { kind: 'money', amount: event.payload.amount },
        ],
        badges: [{ text: 'MORTGAGE', tone: 'warning' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'PROPERTY_UNMORTGAGED':
      return {
        ...base,
        icon: 'U$',
        title: 'Property Unmortgaged',
        severity: 'success',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'unmortgaged' },
          { kind: 'space', spaceIndex: event.payload.space_index },
          { kind: 'text', value: 'for' },
          { kind: 'money', amount: event.payload.amount },
        ],
        badges: [{ text: 'UNMORTGAGE', tone: 'success' }],
        highlightSpaceIndices: [event.payload.space_index],
      };
    case 'LLM_DECISION_REQUESTED':
      return {
        ...base,
        icon: '...',
        title: 'LLM Decision',
        severity: 'info',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: `thinking (${event.payload.decision_type})` },
        ],
        badges: [{ text: 'LLM', tone: 'info' }],
        isMinor: true,
      };
    case 'LLM_DECISION_RESPONSE': {
      const error = event.payload.error;
      const isFallback = typeof error === 'string' && error.startsWith('fallback:');
      const badges: EventBadge[] = [];
      if (!event.payload.valid) {
        badges.push({ text: 'INVALID', tone: 'danger' });
      }
      if (isFallback) {
        badges.push({ text: 'FALLBACK', tone: 'warning' });
      }
      return {
        ...base,
        icon: event.payload.valid ? 'OK' : '!!',
        title: 'LLM Response',
        severity: event.payload.valid ? 'info' : 'danger',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: `chose ${event.payload.action_name}` },
        ],
        badges,
      };
    }
    case 'LLM_PUBLIC_MESSAGE':
      return {
        ...base,
        icon: '""',
        title: 'LLM Message',
        severity: 'neutral',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: `says "${event.payload.message}"` },
        ],
        badges: [],
      };
    case 'LLM_PRIVATE_THOUGHT':
      return {
        ...base,
        icon: '..',
        title: 'LLM Thought',
        severity: 'neutral',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: 'logged a private thought.' },
        ],
        badges: [{ text: 'PRIVATE', tone: 'warning' }],
        isMinor: true,
      };
    default: {
      const unknownType = (event as unknown as { type: string }).type;
      const card = defaultCard(event);
      return {
        ...card,
        parts: [{ kind: 'text', value: `Unknown event: ${unknownType}` }],
      };
    }
  }
};

export const formatSpaceLabel = (spaceIndex: number): string => {
  return `#${spaceIndex} ${getSpaceName(spaceIndex)}`;
};
