import type { Event } from '../../net/contracts';
import { getSpaceName } from './constants';

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
    case 'LLM_DECISION_RESPONSE':
      return {
        ...base,
        icon: event.payload.valid ? 'OK' : '!!',
        title: 'LLM Response',
        severity: event.payload.valid ? 'info' : 'danger',
        parts: [
          { kind: 'player', playerId: event.payload.player_id },
          { kind: 'text', value: `chose ${event.payload.action_name}` },
        ],
        badges: event.payload.valid
          ? []
          : [{ text: 'INVALID', tone: 'danger' }],
      };
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
