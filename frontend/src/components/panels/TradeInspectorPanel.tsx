import { NeoCard } from '@/components/ui/NeoPrimitive';
import { getSpaceName, SPACE_INDEX_BY_KEY } from '@/domain/monopoly/constants';
import { useGameStore } from '@/state/store';

type TradeInspectorPanelProps = {
  visible: boolean;
};

export const TradeInspectorPanel = ({ visible }: TradeInspectorPanelProps) => {
  const snapshot = useGameStore((state) => state.snapshot);
  const trade = snapshot?.trade ?? null;

  if (!visible || !trade) return null;

  const playerMap = new Map(
    (snapshot?.players ?? []).map((player) => [player.player_id, player.name])
  );

  const formatPlayer = (playerId: string | null | undefined) =>
    playerId ? playerMap.get(playerId) ?? playerId : 'Unknown';

  const formatSpaceKey = (spaceKey: string) => {
    const spaceIndex = SPACE_INDEX_BY_KEY[spaceKey];
    return spaceIndex !== undefined ? getSpaceName(spaceIndex) : spaceKey;
  };

  const formatBundle = (bundle: {
    cash: number;
    properties: string[];
    get_out_of_jail_cards: number;
  }) => {
    const parts: string[] = [];
    if (bundle.cash > 0) parts.push(`$${bundle.cash}`);
    if (bundle.properties.length) {
      parts.push(bundle.properties.map(formatSpaceKey).join(', '));
    }
    if (bundle.get_out_of_jail_cards > 0) {
      const label = bundle.get_out_of_jail_cards === 1 ? 'jail card' : 'jail cards';
      parts.push(`${bundle.get_out_of_jail_cards} ${label}`);
    }
    return parts.length ? parts.join(' + ') : 'none';
  };

  return (
    <NeoCard className="p-3 border-3 border-black bg-white">
      <div className="text-xs font-bold uppercase">Trade Inspector</div>
      <div className="text-[10px] font-mono opacity-70 mt-1">
        {formatPlayer(trade.initiator_player_id)}
        {' <-> '}
        {formatPlayer(trade.counterparty_player_id)}
      </div>
      <div className="mt-2 text-[10px] space-y-1">
        <div className="flex justify-between">
          <span className="uppercase text-gray-500">Exchange</span>
          <span className="font-mono">
            {trade.exchange_index}/{trade.max_exchanges}
          </span>
        </div>
        <div>
          <span className="uppercase text-gray-500">Current Offer</span>
          <div className="font-mono mt-1">
            <div>Offer: {formatBundle(trade.current_offer.offer)}</div>
            <div>Request: {formatBundle(trade.current_offer.request)}</div>
          </div>
        </div>
        {trade.history_last_2.length > 0 && (
          <div>
            <span className="uppercase text-gray-500">Recent Exchanges</span>
            <div className="font-mono mt-1 space-y-1">
              {trade.history_last_2.map((entry, index) => (
                <div key={`trade-history-${index}`}>
                  <div>{formatPlayer(entry.from_player_id)}</div>
                  <div className="opacity-80">
                    Offer: {formatBundle(entry.offer)}
                  </div>
                  <div className="opacity-80">
                    Request: {formatBundle(entry.request)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </NeoCard>
  );
};
