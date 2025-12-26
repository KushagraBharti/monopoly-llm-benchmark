import { useState } from 'react';
import { getApiBaseUrl } from '../../net/ws';
import { useGameStore } from '../../state/store';
import { NeoButton, NeoCard } from '../ui/NeoPrimitive';

export const GameControls = () => {
    const [loading, setLoading] = useState(false);
    const status = useGameStore((state) => state.connection.status);
    const snapshot = useGameStore((state) => state.snapshot);
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

    const isRunning = snapshot?.phase && snapshot.phase !== 'GAME_OVER';

    return (
        <NeoCard className="flex flex-col gap-2 p-2">
            <div className="flex justify-between items-center mb-2">
                <span className="font-bold uppercase text-xs tracking-wider">Control Deck</span>
                <div className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-neo-green' : 'bg-red-500'}`} title={status} />
            </div>
            <div className="grid grid-cols-2 gap-2">
                <NeoButton
                    size="sm"
                    variant="primary"
                    onClick={handleStart}
                    disabled={loading}
                >
                    {isRunning ? 'Restart' : 'Start Run'}
                </NeoButton>
                <NeoButton
                    size="sm"
                    variant="ghost"
                    onClick={handleStop}
                    disabled={loading}
                >
                    Stop
                </NeoButton>
            </div>
        </NeoCard>
    );
};
