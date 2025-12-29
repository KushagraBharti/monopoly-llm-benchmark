import { useMemo } from 'react';
import { useGameStore } from '@/state/store';
import { getPlayerIndex } from '@/domain/monopoly/colors';
import { computeNetWorthSimple, selectOwnedSpaces } from '@/domain/monopoly/selectors';
import { PlayerCard } from '@/components/panels/PlayerCard';

type PlayerView = {
  playerId: string;
  name: string;
  cash: number;
  propertyCount: number;
  netWorth: number;
  inJail: boolean;
  bankrupt: boolean;
  modelId: string | null;
  properties: ReturnType<typeof selectOwnedSpaces>;
  latestThought: string | null;
};

export const PlayerStackPanel = () => {
  const snapshot = useGameStore((state) => state.snapshot);
  const runStatus = useGameStore((state) => state.runStatus);
  const events = useGameStore((state) => state.events);
  const deedHighlight = useGameStore((state) => state.ui.deedHighlight);
  const setDeedHighlight = useGameStore((state) => state.setDeedHighlight);
  const activePlayerId = snapshot?.active_player_id ?? null;

  const modelLookup = useMemo(
    () =>
      new Map(
        (runStatus.players ?? []).map((player) => [player.player_id, player.openrouter_model_id ?? player.model_display_name])
      ),
    [runStatus.players]
  );

  const latestThoughtByPlayer = useMemo(() => {
    const map = new Map<string, string>();
    events.forEach((event) => {
      if (event.type !== 'LLM_PRIVATE_THOUGHT') return;
      const playerId = event.payload.player_id;
      if (!map.has(playerId)) {
        map.set(playerId, event.payload.thought);
      }
    });
    return map;
  }, [events]);

  const players = useMemo(() => {
    const snapshotPlayers = snapshot?.players ?? [];
    const snapshotMap = new Map(snapshotPlayers.map((player) => [player.player_id, player]));
    const runStatusPlayers = runStatus.players ?? [];
    const ids = snapshotPlayers.length > 0
      ? snapshotPlayers.map((player) => player.player_id)
      : runStatusPlayers.map((player) => player.player_id);

    return ids
      .filter((id) => id)
      .map((playerId) => {
        const player = snapshotMap.get(playerId);
        const cash = player?.cash ?? 0;
        const properties = selectOwnedSpaces(snapshot, playerId);
        return {
          playerId,
          name: player?.name ?? runStatusPlayers.find((entry) => entry.player_id === playerId)?.name ?? playerId,
          cash,
          propertyCount: properties.length,
          netWorth: computeNetWorthSimple(cash, properties),
          inJail: player?.in_jail ?? false,
          bankrupt: player?.bankrupt ?? false,
          modelId: modelLookup.get(playerId) ?? null,
          properties,
          latestThought: latestThoughtByPlayer.get(playerId) ?? null,
        } satisfies PlayerView;
      })
      .sort((a, b) => getPlayerIndex(a.playerId) - getPlayerIndex(b.playerId));
  }, [snapshot, runStatus.players, modelLookup, latestThoughtByPlayer]);

  if (players.length === 0) {
    return (
      <div className="rounded-sm border-2 border-black bg-white p-3 text-[12px] text-gray-500 shadow-neo-sm">
        Waiting for players...
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 auto-rows-fr">
      {players.map((player) => {
        return (
          <PlayerCard
            key={player.playerId}
            playerId={player.playerId}
            name={player.name}
            modelId={player.modelId}
            cash={player.cash}
            propertyCount={player.propertyCount}
            netWorth={player.netWorth}
            inJail={player.inJail}
            bankrupt={player.bankrupt}
            isActive={player.playerId === activePlayerId}
            properties={player.properties}
            deedHighlight={deedHighlight}
            onToggleHighlight={(index) =>
              setDeedHighlight(deedHighlight === index ? null : index)
            }
            latestThought={player.latestThought}
          />
        );
      })}
    </div>
  );
};
