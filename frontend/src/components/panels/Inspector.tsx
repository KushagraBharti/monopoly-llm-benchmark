import { useMemo, useState } from 'react';
import { useGameStore } from '../../state/store';
import { NeoBadge, cn } from '../ui/NeoPrimitive';

type Tab = 'snapshot' | 'last' | 'stream' | 'raw';

const JsonPane = ({ title, data }: { title: string; data: unknown }) => (
  <div className="flex flex-col gap-1 h-full min-h-0">
    <div className="flex items-center justify-between border-b-2 border-black bg-neo-bg px-2 py-1">
      <span className="text-[10px] uppercase font-black tracking-wider">{title}</span>
      <button
        onClick={() => navigator.clipboard.writeText(JSON.stringify(data, null, 2))}
        className="text-[9px] font-mono hover:text-neo-blue uppercase"
      >
        Copy
      </button>
    </div>
    <div className="flex-1 overflow-auto bg-white p-2 font-mono text-[10px] brutal-scroll">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  </div>
);

const ToggleSwitch = ({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) => (
  <button
    onClick={onClick}
    className={cn(
      "relative px-4 py-1.5 min-w-[80px] text-xs font-bold uppercase transition-all duration-100 border-2 border-black",
      active
        ? "bg-black text-white shadow-none translate-y-[2px] translate-x-[2px]"
        : "bg-white text-black shadow-neo hover:translate-y-[-1px] hover:translate-x-[-1px] hover:shadow-neo-lg"
    )}
  >
    {label}
  </button>
);

export const Inspector = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('snapshot');
  const [showThoughts, setShowThoughts] = useState(false);

  const snapshot = useGameStore((state) => state.snapshot);
  const previousSnapshot = useGameStore((state) => state.previousSnapshot);
  const events = useGameStore((state) => state.events);
  const connection = useGameStore((state) => state.connection);
  const runStatus = useGameStore((state) => state.runStatus);

  const lastEvent = events.length > 0 ? events[0] : null;
  const streamEvents = useMemo(() => {
    const filtered = showThoughts ? events : events.filter((e) => e.type !== 'LLM_PRIVATE_THOUGHT');
    return filtered.slice(0, 100);
  }, [events, showThoughts]);

  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setIsOpen(true)}
          className="w-12 h-12 bg-black border-2 border-neo-white text-white shadow-neo-lg hover:rotate-90 transition-transform duration-300 flex items-center justify-center"
          title="Open Inspector"
        >
          <span className="font-mono text-xl">⚙</span>
        </button>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-[2px] p-4 animate-fade-in-up">
      <div className="w-full max-w-6xl h-[85vh] flex flex-col bg-neo-bg border-4 border-black shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] relative">

        {/* Header Bar */}
        <div className="h-12 bg-black text-white flex justify-between items-center px-4 select-none shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-black uppercase tracking-tighter">System Inspector</h2>
            <div className="hidden md:block h-6 w-[2px] bg-white/30" />
            <div className="hidden md:flex font-mono text-[10px] text-gray-400 gap-4">
              <span>RUN: {snapshot?.run_id?.slice(0, 8) ?? 'N/A'}</span>
              <span>TURN: {snapshot?.turn_index ?? 0}</span>
              <span>SCHEMA: {snapshot?.schema_version ?? '1.0'}</span>
            </div>
          </div>
          {runStatus.players && runStatus.players.length > 0 && runStatus.players.length !== 4 && (
            <NeoBadge variant="warning" className="text-[9px] py-0 px-2">
              PLAYERS {runStatus.players.length}/4
            </NeoBadge>
          )}
          <button
            onClick={() => setIsOpen(false)}
            className="w-8 h-8 flex items-center justify-center bg-neo-red text-white font-bold hover:bg-red-400 transition-colors"
          >
            X
          </button>
        </div>

        {/* Toolbar */}
        <div className="bg-white border-b-2 border-black p-3 flex flex-wrap gap-4 items-center shrink-0">
          <div className="flex items-center gap-2 mr-auto overflow-x-auto pb-1 md:pb-0">
            {(['snapshot', 'last', 'stream', 'raw'] as Tab[]).map((tab) => (
              <ToggleSwitch
                key={tab}
                label={tab}
                active={activeTab === tab}
                onClick={() => setActiveTab(tab)}
              />
            ))}
          </div>

          {activeTab === 'stream' && (
            <label className="flex items-center gap-2 cursor-pointer font-bold text-xs uppercase bg-neo-bg px-2 py-1 border-2 border-black active:translate-y-[1px] select-none">
              <input
                type="checkbox"
                checked={showThoughts}
                onChange={(e) => setShowThoughts(e.target.checked)}
                className="accent-black w-4 h-4"
              />
              Show Thoughts
            </label>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden p-4 bg-neo-bg relative">
          <div className="absolute inset-0 opacity-5 pointer-events-none bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjZmZmIi8+CjxyZWN0IHdpZHRoPSIxIiBoZWlnaHQ9IjEiIGZpbGw9IiMwMDAiLz4KPC9zdmc+')]"></div>

          <div className="h-full bg-white border-2 border-black shadow-neo-sm overflow-hidden flex flex-col relative z-10">
            {activeTab === 'snapshot' && (
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x-2 divide-black overflow-hidden">
                <JsonPane title="Live State" data={snapshot ?? {}} />
                <JsonPane title="Previous State" data={previousSnapshot ?? {}} />
              </div>
            )}

            {activeTab === 'last' && (
              <div className="flex-1 overflow-hidden">
                <JsonPane title="Latest Event Payload" data={lastEvent ?? {}} />
              </div>
            )}

            {activeTab === 'stream' && (
              <div className="flex-1 flex flex-col min-h-0 bg-white">
                <div className="bg-black text-white px-2 py-1 text-[10px] uppercase font-bold flex justify-between">
                  <span>Event Log (Last 100)</span>
                  <span>{streamEvents.length} items</span>
                </div>
                <div className="flex-1 overflow-y-auto brutal-scroll p-0">
                  {streamEvents.length === 0 && (
                    <div className="p-8 text-center text-gray-400 font-mono text-xs">No events to display.</div>
                  )}
                  {streamEvents.map((event, idx) => {
                    const isThought = event.type === 'LLM_PRIVATE_THOUGHT';
                    return (
                      <div
                        key={`${event.event_id}-${idx}`}
                        className={cn(
                          "flex items-baseline gap-2 p-2 border-b border-gray-100 font-mono text-[10px] hover:bg-blue-50 transition-colors",
                          isThought && "bg-gray-50 text-gray-500 italic"
                        )}
                      >
                        <span className="w-8 shrink-0 text-gray-400">#{event.turn_index}</span>
                        <span className={cn("font-bold w-40 shrink-0 truncate", isThought ? "text-gray-500" : "text-blue-700")}>
                          {event.type}
                        </span>
                        <span className="truncate flex-1 opacity-70">
                          {isThought
                            ? (event.payload as any).thought
                            : JSON.stringify(event.payload).slice(0, 100)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {activeTab === 'raw' && (
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x-2 divide-black overflow-hidden">
                <JsonPane title="Websocket Connection" data={connection} />
                <JsonPane title="Runner Status" data={runStatus} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
