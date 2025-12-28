import { useGameStore } from '@/state/store';
import { NeoCard } from '@/components/ui/NeoPrimitive';

export const DecisionOverlay = () => {
  const snapshot = useGameStore((state) => state.snapshot);
  const isVisible = snapshot?.phase === 'AWAITING_DECISION';
  const activePlayerId = snapshot?.active_player_id;

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none">
      <NeoCard className="bg-white border-4 border-black p-4 text-center shadow-neo-lg">
        <div className="text-xs font-bold uppercase">Decision Pending</div>
        <div className="font-mono text-[10px] opacity-70 mt-1">
          Awaiting model tool call
        </div>
        {activePlayerId && (
          <div className="font-mono text-[10px] mt-1">
            Active: {activePlayerId}
          </div>
        )}
      </NeoCard>
    </div>
  );
};
