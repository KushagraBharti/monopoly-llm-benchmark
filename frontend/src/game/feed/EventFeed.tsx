import type { Event, StateSnapshot } from '../../net/contracts'

type EventFeedProps = {
  events: Event[]
  snapshot: StateSnapshot | null
}

const getPlayerName = (snapshot: StateSnapshot | null, playerId: string | null): string => {
  if (!playerId || !snapshot) {
    return playerId ?? 'System'
  }
  return snapshot.players.find((player) => player.player_id === playerId)?.name ?? playerId
}

const getSpaceName = (snapshot: StateSnapshot | null, index: number): string => {
  return snapshot?.board[index]?.name ?? `Space ${index}`
}

const formatEvent = (event: Event, snapshot: StateSnapshot | null): string => {
  switch (event.type) {
    case 'DICE_ROLLED':
      return `${getPlayerName(snapshot, event.actor.player_id)} rolled ${event.payload.d1} + ${event.payload.d2}`
    case 'PLAYER_MOVED':
      return `${getPlayerName(snapshot, event.actor.player_id)} moved ${event.payload.from} -> ${event.payload.to}`
    case 'PROPERTY_PURCHASED':
      return `${getPlayerName(snapshot, event.payload.player_id)} bought ${getSpaceName(
        snapshot,
        event.payload.space_index,
      )} for $${event.payload.price}`
    case 'RENT_PAID':
      return `${getPlayerName(snapshot, event.payload.from_player_id)} paid ${getPlayerName(
        snapshot,
        event.payload.to_player_id,
      )} $${event.payload.amount} rent on ${getSpaceName(snapshot, event.payload.space_index)}`
    case 'CASH_CHANGED': {
      const label = event.payload.delta >= 0 ? 'gained' : 'paid'
      return `${getPlayerName(snapshot, event.payload.player_id)} ${label} $${Math.abs(
        event.payload.delta,
      )} (${event.payload.reason})`
    }
    case 'SENT_TO_JAIL':
      return `${getPlayerName(snapshot, event.payload.player_id)} sent to jail (${event.payload.reason})`
    case 'GAME_ENDED':
      return `Game ended - winner: ${getPlayerName(snapshot, event.payload.winner_player_id)}`
    case 'LLM_PUBLIC_MESSAGE':
      return `${getPlayerName(snapshot, event.payload.player_id)} says: ${event.payload.message}`
    case 'LLM_PRIVATE_THOUGHT':
      return `${getPlayerName(snapshot, event.payload.player_id)} thought: ${event.payload.thought}`
    case 'LLM_DECISION_REQUESTED':
      return `Decision requested: ${getPlayerName(snapshot, event.payload.player_id)}`
    case 'LLM_DECISION_RESPONSE':
      return `Decision response: ${getPlayerName(snapshot, event.payload.player_id)} -> ${
        event.payload.action_name
      }`
    case 'GAME_STARTED':
      return 'Game started'
    case 'TURN_STARTED':
      return 'Turn started'
    case 'TURN_ENDED':
      return 'Turn ended'
    default:
      return event.type
  }
}

export const EventFeed = ({ events, snapshot }: EventFeedProps) => {
  return (
    <div className="event-feed">
      <div className="panel-header">
        <h3>Event Feed</h3>
        <span className="panel-subtitle">Live stream</span>
      </div>
      <div className="event-list">
        {events.length === 0 ? (
          <div className="empty-state">Waiting for events...</div>
        ) : (
          events.map((event, index) => (
            <div
              key={`${event.event_id}-${index}`}
              className="event-card"
              style={{ animationDelay: `${Math.min(index * 40, 240)}ms` }}
            >
              <div className="event-meta">
                <span className="event-seq">#{event.seq}</span>
                <span className="event-turn">T{event.turn_index}</span>
                <span className="event-type">{event.type}</span>
              </div>
              <div className="event-text">{formatEvent(event, snapshot)}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
