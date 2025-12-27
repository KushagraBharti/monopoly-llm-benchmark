import { NeoCard } from '../ui/NeoPrimitive';

type AuctionPanelProps = {
  visible: boolean;
};

export const AuctionPanel = ({ visible }: AuctionPanelProps) => {
  if (!visible) return null;

  return (
    <NeoCard className="p-3 border-3 border-black bg-white">
      <div className="text-xs font-bold uppercase">Auction</div>
      <div className="text-[10px] font-mono opacity-70 mt-1">
        Auction details will appear here.
      </div>
    </NeoCard>
  );
};
