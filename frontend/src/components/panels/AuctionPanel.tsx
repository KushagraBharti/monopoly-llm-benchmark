import { NeoCard } from '@/components/ui/NeoPrimitive';
import { useGameStore } from '@/state/store';
import { getSpaceName, SPACE_INDEX_BY_KEY } from '@/domain/monopoly/constants';

type AuctionPanelProps = {
  visible: boolean;
};

export const AuctionPanel = ({ visible }: AuctionPanelProps) => {
  const snapshot = useGameStore((state) => state.snapshot);
  const auction = snapshot?.auction ?? null;

  if (!visible || !auction) return null;

  const playerMap = new Map(
    (snapshot?.players ?? []).map((player) => [player.player_id, player.name])
  );
  const spaceIndex = SPACE_INDEX_BY_KEY[auction.property_space_key] ?? null;
  const spaceLabel =
    spaceIndex !== null ? `${getSpaceName(spaceIndex)}` : auction.property_space_key;
  const currentLeader = auction.current_leader_player_id
    ? playerMap.get(auction.current_leader_player_id) ?? auction.current_leader_player_id
    : null;
  const currentBidder = auction.current_bidder_player_id
    ? playerMap.get(auction.current_bidder_player_id) ?? auction.current_bidder_player_id
    : null;
  const minNextBid = auction.current_high_bid + 1;
  const activeBidders = auction.active_bidders_player_ids.map(
    (playerId) => playerMap.get(playerId) ?? playerId
  );

  return (
    <NeoCard className="p-3 border-3 border-black bg-white">
      <div className="text-xs font-bold uppercase">Auction</div>
      <div className="text-[10px] font-mono opacity-70 mt-1">
        {spaceLabel}
      </div>
      <div className="mt-2 text-[10px] space-y-1">
        <div className="flex justify-between">
          <span className="uppercase text-gray-500">High Bid</span>
          <span className="font-mono">${auction.current_high_bid}</span>
        </div>
        <div className="flex justify-between">
          <span className="uppercase text-gray-500">Min Next Bid</span>
          <span className="font-mono">${minNextBid}</span>
        </div>
        <div className="flex justify-between">
          <span className="uppercase text-gray-500">Leader</span>
          <span className="font-mono">{currentLeader ?? 'None'}</span>
        </div>
        <div className="flex justify-between">
          <span className="uppercase text-gray-500">Current Bidder</span>
          <span className="font-mono">{currentBidder ?? 'Unknown'}</span>
        </div>
        <div>
          <span className="uppercase text-gray-500">Active Bidders</span>
          <div className="font-mono mt-1">{activeBidders.join(', ') || 'None'}</div>
        </div>
      </div>
    </NeoCard>
  );
};
