import { useState } from 'react';
import { useGameStore } from '../../state/store';
import { NeoButton, NeoCard } from '../ui/NeoPrimitive';

export const Inspector = () => {
    const [isOpen, setIsOpen] = useState(false);
    const snapshot = useGameStore((state) => state.snapshot);
    const events = useGameStore((state) => state.events);
    const connection = useGameStore((state) => state.connection);

    const privateThoughts = events.filter(e => e.type === 'LLM_PRIVATE_THOUGHT');

    if (!isOpen) {
        return (
            <div className="fixed bottom-4 right-4 z-50">
                <NeoButton onClick={() => setIsOpen(true)} size="sm" variant="secondary">
                    Debug Inspector
                </NeoButton>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-8 backdrop-blur-sm">
            <NeoCard className="w-full max-w-4xl h-[80vh] flex flex-col relative bg-neo-bg">
                <div className="flex justify-between items-center border-b-2 border-black pb-4 mb-4">
                    <h2 className="text-2xl">System Inspector</h2>
                    <NeoButton onClick={() => setIsOpen(false)} size="sm" variant="danger">Close</NeoButton>
                </div>

                <div className="flex-1 overflow-hidden grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2 overflow-hidden">
                        <h3 className="text-lg font-bold">Latest Snapshot</h3>
                        <pre className="flex-1 overflow-auto text-[10px] bg-white border-2 border-black p-2 font-mono">
                            {JSON.stringify(snapshot, null, 2)}
                        </pre>
                    </div>

                    <div className="flex flex-col gap-2 overflow-hidden">
                        <h3 className="text-lg font-bold">Private Thoughts ({privateThoughts.length})</h3>
                        <div className="flex-1 overflow-auto bg-white border-2 border-black p-2 space-y-2">
                            {privateThoughts.length === 0 && <span className="opacity-50 text-sm">No thoughts recorded yet.</span>}
                            {privateThoughts.map(t => (
                                <div key={t.event_id} className="p-2 border-b border-black/10 text-xs">
                                    <div className="font-bold mb-1">{t.actor.player_id}</div>
                                    <div className="font-serif italic bg-slate-100 p-1">{(t.payload as any).thought}</div>
                                </div>
                            ))}
                        </div>
                        <div className="h-1/3 border-t-2 border-black pt-2 flex flex-col">
                            <span className="font-bold text-sm">Connection Status</span>
                            <pre className="text-xs">{JSON.stringify(connection, null, 2)}</pre>
                        </div>
                    </div>
                </div>
            </NeoCard>
        </div>
    );
};
