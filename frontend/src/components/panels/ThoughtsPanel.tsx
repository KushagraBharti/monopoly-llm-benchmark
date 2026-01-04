import { useMemo, useState } from 'react';
import type { Event } from '@/net/contracts';
import { useGameStore } from '@/state/store';
import { getPlayerIndex } from '@/domain/monopoly/colors';
import { cn } from '@/components/ui/cn';

type PrivateThoughtEvent = Extract<Event, { type: 'LLM_PRIVATE_THOUGHT' }>;

type ThoughtEntry = {
  eventId: string;
  decisionId: string | null;
  playerId: string;
  thought: string;
  turnIndex: number;
  seq: number;
};

type ThoughtGroup = {
  key: string;
  decisionId: string | null;
  turnIndex: number;
  entries: ThoughtEntry[];
};

const buildThoughtEntries = (events: Event[], playerId: string): ThoughtEntry[] => {
  return events
    .filter(
      (event): event is PrivateThoughtEvent =>
        event.type === 'LLM_PRIVATE_THOUGHT' && event.payload.player_id === playerId
    )
    .map((event) => ({
      eventId: event.event_id,
      decisionId: event.payload.decision_id ?? null,
      playerId: event.payload.player_id,
      thought: event.payload.thought,
      turnIndex: event.turn_index,
      seq: event.seq,
    }))
    .sort((a, b) => a.seq - b.seq);
};

const groupThoughts = (entries: ThoughtEntry[]): ThoughtGroup[] => {
  const groups = new Map<string, ThoughtGroup>();
  entries.forEach((entry) => {
    const key = entry.decisionId ?? entry.eventId;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        decisionId: entry.decisionId,
        turnIndex: entry.turnIndex,
        entries: [],
      });
    }
    groups.get(key)?.entries.push(entry);
  });
  return Array.from(groups.values());
};

export const ThoughtsPanel = () => {
  const snapshot = useGameStore((state) => state.snapshot);
  const runStatus = useGameStore((state) => state.runStatus);
  const events = useGameStore((state) => state.events);
  const [isOpen, setIsOpen] = useState(true);

  const players = useMemo(() => {
    const snapshotPlayers = snapshot?.players ?? [];
    const runPlayers = runStatus.players ?? [];
    const ids = snapshotPlayers.length > 0
      ? snapshotPlayers.map((player) => player.player_id)
      : runPlayers.map((player) => player.player_id);
    const names = new Map(snapshotPlayers.map((player) => [player.player_id, player.name]));
    runPlayers.forEach((entry) => {
      if (!names.has(entry.player_id)) {
        names.set(entry.player_id, entry.name);
      }
    });
    return ids
      .filter((id) => id)
      .map((playerId) => ({
        playerId,
        name: names.get(playerId) ?? playerId,
      }))
      .sort((a, b) => getPlayerIndex(a.playerId) - getPlayerIndex(b.playerId));
  }, [snapshot, runStatus.players]);

  const [activePlayerId, setActivePlayerId] = useState<string | null>(null);
  const resolvedActivePlayerId = useMemo(() => {
    if (players.length === 0) return null;
    if (activePlayerId && players.some((player) => player.playerId === activePlayerId)) {
      return activePlayerId;
    }
    return players[0].playerId;
  }, [players, activePlayerId]);

  const thoughts = useMemo(() => {
    if (!resolvedActivePlayerId) return [];
    const entries = buildThoughtEntries(events, resolvedActivePlayerId);
    return groupThoughts(entries);
  }, [events, resolvedActivePlayerId]);

  const activeName = players.find((player) => player.playerId === resolvedActivePlayerId)?.name ?? 'Player';

  if (players.length === 0) {
    return null;
  }

  return (
    <div className="rounded-sm border border-neo-border bg-white overflow-hidden">
      <div className="flex items-center justify-between px-2 py-1 border-b border-gray-200">
        <div className="text-[10px] font-bold uppercase tracking-wider">Thoughts</div>
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="text-[9px] font-mono text-gray-600 hover:text-black"
        >
          {isOpen ? 'Hide' : 'Show'}
        </button>
      </div>

      {isOpen && (
        <div className="p-2 flex flex-col gap-2">
          <div className="flex flex-wrap gap-1">
            {players.map((player) => (
              <button
                key={player.playerId}
                type="button"
                onClick={() => setActivePlayerId(player.playerId)}
                className={cn(
                  'px-2 py-0.5 text-[9px] font-bold uppercase border border-gray-300 rounded-sm',
                  resolvedActivePlayerId === player.playerId
                    ? 'bg-black text-white border-black'
                    : 'bg-white text-gray-700 hover:border-gray-500'
                )}
              >
                {player.name}
              </button>
            ))}
          </div>

          <div className="text-[9px] text-gray-500 uppercase tracking-wide">
            {activeName} private thoughts
          </div>

          <div className="flex flex-col gap-2 max-h-[280px] overflow-y-auto pr-1 brutal-scroll">
            {thoughts.length === 0 && (
              <div className="text-[10px] text-gray-400">No private thoughts yet.</div>
            )}
            {thoughts.map((group) => (
              <details
                key={group.key}
                className="border border-gray-200 rounded-sm bg-gray-50"
                open
              >
                <summary className="px-2 py-1 cursor-pointer text-[9px] font-mono text-gray-700">
                  Turn {group.turnIndex}
                  {group.decisionId ? ` - ${group.decisionId}` : ''}
                </summary>
                <div className="px-2 py-1 text-[10px] text-gray-800 space-y-1">
                  {group.entries.map((entry) => (
                    <div key={entry.eventId} className="whitespace-pre-wrap">
                      {entry.thought}
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
