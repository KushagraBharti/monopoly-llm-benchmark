import { useRef, useState } from 'react';
import { getApiBaseUrl } from '@/net/ws';
import { useGameStore } from '@/state/store';
import { NeoBadge, NeoCard, cn } from '@/components/ui/NeoPrimitive';

export const GameControls = () => {
  const [loadingAction, setLoadingAction] = useState<null | 'start' | 'stop' | 'pause' | 'resume'>(null);
  const [pendingStart, setPendingStart] = useState(false);
  const [pendingResume, setPendingResume] = useState(false);
  const pendingStartRef = useRef(false);
  const pendingResumeRef = useRef(false);
  const runStatus = useGameStore((state) => state.runStatus);
  const setRunStatus = useGameStore((state) => state.setRunStatus);
  const resetLogs = useGameStore((state) => state.resetLogs);
  const apiBase = getApiBaseUrl();

  const handleStart = async () => {
    if (loadingAction || pendingStartRef.current || pendingResumeRef.current || runStatus.running) return;
    pendingStartRef.current = true;
    setPendingStart(true);
    setLoadingAction('start');
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
      setLoadingAction(null);
      pendingStartRef.current = false;
      setPendingStart(false);
    }
  };

  const handleStop = async () => {
    if (loadingAction || pendingStartRef.current || pendingResumeRef.current) return;
    setLoadingAction('stop');
    resetLogs();
    setRunStatus({ running: false, paused: false });
    try {
      await fetch(`${apiBase}/run/stop`, { method: 'POST' });
    } catch (e) {
      console.error(e);
      alert('Failed to stop run');
    } finally {
      setLoadingAction(null);
    }
  };

  const handlePause = async () => {
    if (loadingAction || pendingStartRef.current || pendingResumeRef.current || !runStatus.running || runStatus.paused) return;
    setLoadingAction('pause');
    try {
      await fetch(`${apiBase}/run/pause`, { method: 'POST' });
      setRunStatus({ paused: true });
    } catch (e) {
      console.error(e);
      alert('Failed to pause run');
    } finally {
      setLoadingAction(null);
    }
  };

  const handleResume = async () => {
    if (loadingAction || pendingStartRef.current || pendingResumeRef.current || !runStatus.running || !runStatus.paused) return;
    pendingResumeRef.current = true;
    setPendingResume(true);
    setLoadingAction('resume');
    try {
      await fetch(`${apiBase}/run/resume`, { method: 'POST' });
      setRunStatus({ paused: false });
    } catch (e) {
      console.error(e);
      alert('Failed to resume run');
    } finally {
      setLoadingAction(null);
      pendingResumeRef.current = false;
      setPendingResume(false);
    }
  };

  const isRunning = runStatus.running;
  const isPaused = runStatus.paused;
  const isLoading = loadingAction !== null || pendingStart || pendingResume;

  return (
    <NeoCard className="flex flex-col gap-2 p-2 border-neo-border bg-white shadow-neo">
      <div className="flex justify-between items-center mb-1 px-1">
        <span className="text-[10px] font-black uppercase tracking-wider">Session Control</span>
        <div className="flex items-center gap-2">
          {isPaused && (
            <NeoBadge variant="warning" className="text-[9px] py-0 px-1">
              PAUSED
            </NeoBadge>
          )}
          {isLoading && <span className="animate-spin">?</span>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleStart}
          disabled={isLoading || isRunning}
          className="brutal-btn bg-neo-black text-white hover:bg-neutral-800 disabled:opacity-50 w-full"
        >
          {isRunning ? 'RUNNING' : 'START RUN'}
        </button>

        <button
          onClick={handleStop}
          disabled={isLoading || !isRunning}
          className="brutal-btn bg-white hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed text-neo-red border-neo-red w-full"
        >
          STOP
        </button>
      </div>

      <div className="grid grid-cols-1">
        <button
          onClick={isPaused ? handleResume : handlePause}
          disabled={isLoading || !isRunning}
          className={cn(
            'brutal-btn w-full',
            isPaused ? 'bg-neo-green text-black hover:bg-green-300' : 'bg-neo-yellow text-black hover:bg-yellow-300'
          )}
        >
          {isPaused ? 'RESUME' : 'PAUSE'}
        </button>
      </div>
    </NeoCard>
  );
};
