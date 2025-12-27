import { useState } from 'react';
import { useGameStore } from '../../state/store';
import { NeoButton, NeoCard, cn } from '../ui/NeoPrimitive';

type Tab = 'snapshot' | 'events' | 'stream' | 'system';

export const Inspector = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<Tab>('snapshot');
    const [showThoughts, setShowThoughts] = useState(false);

    const snapshot = useGameStore((state) => state.snapshot);
    const events = useGameStore((state) => state.events);
    const connection = useGameStore((state) => state.connection);

    const privateThoughts = events.filter(e => e.type === 'LLM_PRIVATE_THOUGHT');
    const lastEvent = events.length > 0 ? events[events.length - 1] : null;

    if (!isOpen) {
        return (
            <div className="fixed bottom-4 right-4 z-50">
                <NeoButton onClick={() => setIsOpen(true)} size="sm" variant="secondary" className="shadow-2xl">
                    🐞 Inspector
                </NeoButton>
            </div>
        );
    }

    const renderTabContent = () => {
        switch (activeTab) {
            case 'snapshot':
                return (
                    <div className="flex-1 overflow-auto bg-gray-50 border-2 border-black p-2 font-mono text-[10px]">
                        <pre>{JSON.stringify(snapshot, null, 2)}</pre>
                    </div>
                );
            case 'events':
                return (
                    <div className="flex-1 overflow-hidden flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <h3 className="font-bold">Private Thoughts ({privateThoughts.length})</h3>
                            <label className="text-xs flex items-center gap-1 cursor-pointer select-none">
                                <input type="checkbox" checked={showThoughts} onChange={e => setShowThoughts(e.target.checked)} />
                                Show All
                            </label>
                        </div>
                        <div className="flex-1 overflow-auto border-2 border-black bg-white p-2 space-y-2">
                            {privateThoughts.length === 0 && <span className="opacity-50 text-sm">No thoughts recorded.</span>}
                            {privateThoughts.map((t, i) => (
                                <div key={i} className="p-2 border-b border-dashed border-black/20 text-xs">
                                    <div className="font-bold mb-1 text-neo-pink">{t.actor?.player_id}</div>
                                    <div className="font-serif italic text-gray-700 bg-gray-100 p-1">{(t.payload as any).thought}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            case 'stream':
                return (
                    <div className="flex-1 overflow-hidden flex flex-col gap-2">
                        <h3 className="font-bold">Last Event</h3>
                        <div className="h-48 overflow-auto border-2 border-black bg-white p-2 font-mono text-[10px]">
                            <pre>{JSON.stringify(lastEvent, null, 2)}</pre>
                        </div>
                        <h3 className="font-bold">Event Log (Raw)</h3>
                        <div className="flex-1 overflow-auto border-2 border-black bg-gray-100 p-2 font-mono text-[10px]">
                            {events.slice().reverse().map((e, i) => (
                                <div key={i} className="mb-1 border-b border-gray-300 pb-1">
                                    <span className="text-blue-600 font-bold">{e.type}</span> <span className="text-gray-500">#{e.turn_index}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            case 'system':
                return (
                    <div className="flex-1 overflow-auto font-mono text-xs">
                        <h3 className="font-bold mb-2">Connection Status</h3>
                        <pre className="md-2 bg-gray-100 p-2 border border-black">{JSON.stringify(connection, null, 2)}</pre>
                    </div>
                );
            default:
                return null;
        }
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 md:p-8 animate-fade-in">
            <NeoCard className="w-full max-w-5xl h-[85vh] flex flex-col bg-neo-bg shadow-2xl relative">
                {/* Header */}
                <div className="flex justify-between items-center border-b-2 border-black pb-2 mb-2 bg-white -m-4 mb-4 p-4 rounded-t-sm">
                    <h2 className="text-xl font-black uppercase flex items-center gap-2">
                        🐞 System Inspector
                    </h2>
                    <NeoButton onClick={() => setIsOpen(false)} size="sm" variant="danger">Close</NeoButton>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-4">
                    {(['snapshot', 'events', 'stream', 'system'] as Tab[]).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={cn(
                                "px-4 py-1 text-sm font-bold uppercase border-2 border-black transition-all",
                                activeTab === tab ? "bg-black text-white shadow-[2px_2px_0px_0px_#888]" : "bg-white hover:bg-gray-100 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[-1px]"
                            )}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden flex flex-col bg-white border-2 border-black p-4 shadow-inner">
                    {renderTabContent()}
                </div>
            </NeoCard>
        </div>
    );
};
