import type { Space } from '@/net/contracts';
import { getPlayerColor, getPlayerInitials } from '@/domain/monopoly/colors';
import { NeoCard, cn } from '@/components/ui/NeoPrimitive';
import { PropertyChip } from '@/components/panels/PropertyChip';

const formatMoney = (value: number): string => {
  return value.toLocaleString('en-US');
};

type PlayerCardProps = {
  playerId: string;
  name: string;
  modelId: string | null;
  cash: number;
  propertyCount: number;
  netWorth: number;
  inJail: boolean;
  bankrupt: boolean;
  isActive: boolean;
  properties: Space[];
  deedHighlight: number | null;
  onToggleHighlight: (index: number) => void;
  latestThought: string | null;
};

export const PlayerCard = ({
  playerId,
  name,
  modelId,
  cash,
  propertyCount,
  netWorth,
  inJail,
  bankrupt,
  isActive,
  properties,
  deedHighlight,
  onToggleHighlight,
  latestThought,
}: PlayerCardProps) => {
  const badgeColor = getPlayerColor(playerId);

  return (
    <NeoCard
      className={cn(
        'p-3 flex flex-col gap-2 h-full',
        isActive ? 'bg-neo-yellow/20' : 'bg-white'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <div
            className="w-4 h-4 rounded-sm border-2 border-black shrink-0"
            style={{ backgroundColor: badgeColor }}
            title={`Player ${playerId}`}
          />
          <div className="min-w-0">
            <div className={cn('text-[12px] font-black uppercase truncate', bankrupt && 'line-through opacity-60')}>
              {name || getPlayerInitials(playerId)}
            </div>
            <div className="text-[10px] text-gray-600 font-mono truncate max-w-[160px]">
              {modelId ?? 'model unknown'}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          {isActive && (
            <span className="text-[9px] font-black uppercase text-neo-blue">Active</span>
          )}
          {(inJail || bankrupt) && (
            <div className="flex gap-1">
              {inJail && <span className="text-[9px] font-black uppercase text-neo-orange">Jail</span>}
              {bankrupt && <span className="text-[9px] font-black uppercase text-neo-red">Bankrupt</span>}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-[11px] text-gray-700">
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-wide">Cash</span>
          <span className="font-mono text-[12px] text-black">${formatMoney(cash)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-wide">Props</span>
          <span className="font-mono text-[12px] text-black">{propertyCount}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-wide">Net</span>
          <span
            className="font-mono text-[12px] text-black"
            title="Net worth = cash + sum(price) - sum(price/2 for mortgaged)"
          >
            ${formatMoney(netWorth)}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[9px] uppercase tracking-wide text-gray-600">Properties</span>
        <div className="flex flex-wrap gap-1">
          {properties.length > 0 ? (
            properties.map((space) => (
              <PropertyChip
                key={space.index}
                space={space}
                isSelected={deedHighlight === space.index}
                onSelect={() => onToggleHighlight(space.index)}
              />
            ))
          ) : (
            <span className="text-[10px] text-gray-500">No properties</span>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-1 border-t border-black/10 pt-2">
        <span className="text-[9px] uppercase tracking-wide text-gray-600">Latest Thought</span>
        <div
          className="text-[11px] text-gray-800 min-h-[18px] whitespace-pre-wrap"
        >
          {latestThought ?? <span className="text-gray-400">No private thoughts yet.</span>}
        </div>
      </div>
    </NeoCard>
  );
};
