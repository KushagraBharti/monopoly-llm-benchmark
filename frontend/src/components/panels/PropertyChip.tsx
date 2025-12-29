import type { Space } from '@/net/contracts';
import { getGroupColor } from '@/domain/monopoly/colors';
import { cn } from '@/components/ui/NeoPrimitive';

const formatChipLabel = (name: string): string => {
  const cleaned = name
    .replace(/\b(Avenue|Street|Place|Railroad|Company|Gardens|Park|Line|Works)\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  const base = cleaned.length > 0 ? cleaned : name;
  const words = base.split(' ');
  const short = words.slice(0, 2).join(' ');
  return short.length > 10 ? short.slice(0, 10) : short;
};

const buildTitle = (space: Space): string => {
  const parts = [space.name];
  if (space.group) {
    parts.push(`Group: ${space.group}`);
  }
  if (space.mortgaged) {
    parts.push('Mortgaged');
  }
  if (space.hotel) {
    parts.push('Hotel');
  } else if (space.houses > 0) {
    parts.push(`Houses: ${space.houses}`);
  }
  return parts.join(' - ');
};

type PropertyChipProps = {
  space: Space;
  isSelected: boolean;
  onSelect: () => void;
};

export const PropertyChip = ({ space, isSelected, onSelect }: PropertyChipProps) => {
  const groupColor = getGroupColor(space.group);
  const label = formatChipLabel(space.name);

  return (
    <button
      type="button"
      onClick={onSelect}
      title={buildTitle(space)}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1 rounded-sm border-2 text-[9px] font-bold uppercase tracking-wide transition-all shadow-neo-sm',
        'bg-white text-gray-900 border-black hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-neo',
        space.mortgaged && 'opacity-70',
        isSelected && 'ring-2 ring-neo-pink'
      )}
    >
      <span
        className="w-2.5 h-2.5 rounded-[2px] border-2 border-black"
        style={{ backgroundColor: groupColor }}
      />
      <span className="truncate max-w-[90px]">{label}</span>
      {space.mortgaged && <span className="text-[8px] font-black text-neo-red">M</span>}
    </button>
  );
};
