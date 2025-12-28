import { useState } from 'react';
import { getApiBaseUrl } from '@/net/ws';
import { useGameStore } from '@/state/store';
import { NeoCard } from '@/components/ui/NeoPrimitive';

export const GameControls = () => {
    const [loading, setLoading] = useState(false);
    const runStatus = useGameStore((state) => state.runStatus);
    const apiBase = getApiBaseUrl();

    const handleStart = async () => {
        if (loading) return;
        setLoading(true);
        try {
            await fetch(`${apiBase}/run/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seed: Date.now() % 100000 }),
            });
        } catch (e) {
            console.error(e);
            alert('Failed to start run');
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        if (loading) return;
        setLoading(true);
        try {
            await fetch(`${apiBase}/run/stop`, { method: 'POST' });
        } catch (e) {
            console.error(e);
            alert('Failed to stop run');
        } finally {
            setLoading(false);
        }
    };

    const isRunning = runStatus.running;

    return (
        <NeoCard className="flex flex-col gap-2 p-2 border-neo-border bg-white shadow-neo">
            <div className="flex justify-between items-center mb-1 px-1">
                <span className="text-[10px] font-black uppercase tracking-wider">Session Control</span>
                {loading && <span className="animate-spin">⏳</span>}
            </div>

            <div className="grid grid-cols-2 gap-3">
                <button
                    onClick={handleStart}
                    disabled={loading}
                    className="brutal-btn bg-neo-black text-white hover:bg-neutral-800 disabled:opacity-50 w-full"
                >
                    {isRunning ? 'RESTART' : 'START RUN'}
                </button>

                <button
                    onClick={handleStop}
                    disabled={loading || !isRunning}
                    className="brutal-btn bg-white hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed text-neo-red border-neo-red w-full"
                >
                    STOP
                </button>
            </div>
        </NeoCard>
    );
};
