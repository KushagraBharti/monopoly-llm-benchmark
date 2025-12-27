import { useState } from 'react';
import { getApiBaseUrl } from '../../net/ws';
import { useGameStore } from '../../state/store';
import { NeoButton, NeoCard } from '../ui/NeoPrimitive';

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
        <NeoCard className="flex flex-col gap-2 p-2" variant="flat">
            <div className="grid grid-cols-2 gap-2">
                <NeoButton
                    size="sm"
                    variant="primary"
                    onClick={handleStart}
                    disabled={loading}
                    className="w-full"
                >
                    {isRunning ? 'Restart' : 'Start Run'}
                </NeoButton>
                <NeoButton
                    size="sm"
                    variant="ghost"
                    onClick={handleStop}
                    disabled={loading || !isRunning}
                    className="w-full"
                >
                    Stop
                </NeoButton>
            </div>
        </NeoCard>
    );
};
