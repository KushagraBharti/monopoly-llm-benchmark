import { useMemo, useState } from 'react';
import { useGameStore } from '../../state/store';
import { NeoButton, NeoCard, cn } from '../ui/NeoPrimitive';

type Tab = 'snapshot' | 'last' | 'stream' | 'raw';

const JsonPane = ({ title, data }: { title: string; data: unknown }) => (
  <div className="flex flex-col gap-1">
    <div className="flex items-center justify-between">
      <span className="text-[9px] uppercase font-bold">{title}</span>
    </div>
    <div className="border-2 border-black bg-gray-50 p-2 font-mono text-[10px] overflow-auto max-h-[50vh]">
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  </div>
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
    return filtered.slice(0, 80);
  }, [events, showThoughts]);

  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <NeoButton onClick={() => setIsOpen(true)} size="sm" variant="secondary" className="shadow-2xl">
          Inspector
        </NeoButton>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 md:p-8 animate-fade-in">
      <NeoCard className="w-full max-w-6xl h-[85vh] flex flex-col bg-neo-bg shadow-2xl relative">
        <div className="flex justify-between items-center border-b-2 border-black pb-2 mb-2 bg-white -m-4 mb-4 p-4 rounded-t-sm">
          <div>
            <h2 className="text-xl font-black uppercase">System Inspector</h2>
            <div className="text-[10px] font-mono text-gray-600">
              schema={snapshot?.schema_version ?? 'n/a'} | run={snapshot?.run_id ?? 'n/a'} | turn={snapshot?.turn_index ?? 0}
            </div>
          </div>
          <NeoButton onClick={() => setIsOpen(false)} size="sm" variant="danger">
            Close
          </NeoButton>
        </div>

        <div className="flex gap-2 mb-4">
          {(['snapshot', 'last', 'stream', 'raw'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-1 text-sm font-bold uppercase border-2 border-black transition-all',
                activeTab === tab
                  ? 'bg-black text-white shadow-[2px_2px_0px_0px_#888]'
                  : 'bg-white hover:bg-gray-100 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[-1px]'
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-hidden flex flex-col bg-white border-2 border-black p-4 shadow-inner">
          {activeTab === 'snapshot' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <JsonPane title="Current Snapshot" data={snapshot ?? {}} />
              <JsonPane title="Previous Snapshot" data={previousSnapshot ?? {}} />
            </div>
          )}

          {activeTab === 'last' && (
            <JsonPane title="Last Event" data={lastEvent ?? {}} />
          )}

          {activeTab === 'stream' && (
            <div className="flex-1 overflow-hidden flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <h3 className="font-bold">Recent Stream</h3>
                <label className="text-xs flex items-center gap-1 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={showThoughts}
                    onChange={(e) => setShowThoughts(e.target.checked)}
                  />
                  Show Private Thoughts
                </label>
              </div>
              <div className="flex-1 overflow-auto border-2 border-black bg-gray-50 p-2 font-mono text-[10px]">
                {streamEvents.length === 0 && (
                  <div className="opacity-50">No events.</div>
                )}
                {streamEvents.map((event) => (
                  <div key={event.event_id} className="border-b border-dashed border-black/20 py-1">
                    <span className="font-bold">{event.type}</span>{' '}
                    <span className="opacity-60">#{event.turn_index}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'raw' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <JsonPane title="Connection" data={connection} />
              <JsonPane title="Run Status" data={runStatus} />
            </div>
          )}
        </div>
      </NeoCard>
    </div>
  );
};
