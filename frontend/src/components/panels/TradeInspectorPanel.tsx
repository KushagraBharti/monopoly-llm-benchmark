import { NeoCard } from '@/components/ui/NeoPrimitive';

type TradeInspectorPanelProps = {
  visible: boolean;
};

export const TradeInspectorPanel = ({ visible }: TradeInspectorPanelProps) => {
  if (!visible) return null;

  return (
    <NeoCard className="p-3 border-3 border-black bg-white">
      <div className="text-xs font-bold uppercase">Trade Inspector</div>
      <div className="text-[10px] font-mono opacity-70 mt-1">
        Trade details will appear here.
      </div>
    </NeoCard>
  );
};
