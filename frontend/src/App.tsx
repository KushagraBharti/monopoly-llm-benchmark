import { useEffect, useMemo, useRef } from 'react';
import { getApiBaseUrl, getWsUrl, WsClient } from '@/net/ws';
import { useGameStore } from '@/state/store';
import { Board } from '@/components/board/Board';
import { PlayerPanel } from '@/components/panels/PlayerPanel';
import { OwnershipPanel } from '@/components/panels/OwnershipPanel';
import { EventFeed } from '@/components/feed/EventFeed';
import { GameControls } from '@/components/panels/GameControls';
import { Inspector } from '@/components/panels/Inspector';
import { DecisionOverlay } from '@/components/panels/DecisionOverlay';
import { AuctionPanel } from '@/components/panels/AuctionPanel';
import { TradeInspectorPanel } from '@/components/panels/TradeInspectorPanel';
import { NeoBadge, cn } from '@/components/ui/NeoPrimitive';
import { GO_INDEX, JAIL_INDEX } from '@/domain/monopoly/constants';
import type { Event } from '@/net/contracts';

function App() {
  const setStatus = useGameStore((state) => state.setStatus);
  const setSnapshot = useGameStore((state) => state.setSnapshot);
  const pushEvent = useGameStore((state) => state.pushEvent);
  const setRunStatus = useGameStore((state) => state.setRunStatus);
  const setEventHighlight = useGameStore((state) => state.setEventHighlight);
  const snapshot = useGameStore((state) => state.snapshot);
  const connection = useGameStore((state) => state.connection);
  const runStatus = useGameStore((state) => state.runStatus);
  const latestEvent = useGameStore((state) => state.events[0]);
  const apiBase = useMemo(() => getApiBaseUrl(), []);
  const highlightTimerRef = useRef<number | null>(null);

  const runState = useMemo(() => {
    if (runStatus.running) return 'RUNNING';
    if (runStatus.runId) return 'COMPLETE';
    return 'IDLE';
  }, [runStatus.running, runStatus.runId]);

  const showAuction = false;
  const showTrade = false;

  useEffect(() => {
    const client = new WsClient(getWsUrl(), {
      onHello: (payload) => setRunStatus({ runId: payload.run_id }),
      onSnapshot: (payload) => setSnapshot(payload),
      onEvent: (payload) => pushEvent(payload),
      onError: (payload) => setStatus('disconnected', payload.message),
      onStatusChange: (status, error) => setStatus(status, error),
    });
    client.connect();
    return () => client.close();
  }, [pushEvent, setRunStatus, setSnapshot, setStatus]);

  useEffect(() => {
    let active = true;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${apiBase}/run/status`);
        if (!res.ok) return;
        const data = (await res.json()) as {
          running: boolean;
          run_id: string | null;
          turn_index: number | null;
          connected_clients: number;
          players?: {
            player_id: string;
            name: string;
            model_display_name: string;
            openrouter_model_id: string;
          }[];
        };
        if (!active) return;
        setRunStatus({
          running: data.running,
          runId: data.run_id,
          turnIndex: data.turn_index ?? null,
          connectedClients: data.connected_clients,
          players: data.players ?? [],
        });
      } catch {
        if (!active) return;
      }
    };
    fetchStatus();
    const interval = window.setInterval(fetchStatus, 2500);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [apiBase, setRunStatus]);

  useEffect(() => {
    if (!latestEvent) return;
    const highlightIndices = getHighlightIndices(latestEvent);
    if (!highlightIndices.length) return;
    setEventHighlight(highlightIndices);
    if (highlightTimerRef.current) {
      window.clearTimeout(highlightTimerRef.current);
    }
    highlightTimerRef.current = window.setTimeout(() => {
      setEventHighlight(null);
    }, 1400);
    return () => {
      if (highlightTimerRef.current) {
        window.clearTimeout(highlightTimerRef.current);
      }
    };
  }, [latestEvent?.event_id, setEventHighlight]);

  // Status Derivation
  const isConnected = connection.status === 'connected';
  const runBadgeLabel = runState === 'RUNNING' ? 'RUNNING' : runState === 'COMPLETE' ? 'COMPLETE' : 'IDLE';

  return (
    <div className="h-screen w-screen bg-neo-bg text-black font-sans overflow-hidden flex relative">

      {/* Sidebar: Left Panel (Players & Controls & Ownership) */}
      <aside className="w-80 h-full border-r-4 border-black bg-white flex flex-col z-30 shadow-neo-lg">
        <header className="p-2 border-b-2 border-black bg-gray-50 shrink-0">
          <h1 className="text-xl font-black uppercase tracking-tighter leading-none mb-1">
            Monopoly <span className="text-neo-pink">Arena</span>
          </h1>

          <div className="flex flex-col gap-1 mt-0.5">
            {/* Connection Status */}
            <div className="flex justify-between items-center">
              <span className="text-[9px] font-bold uppercase text-gray-500 flex items-center gap-1">
                <span className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  isConnected ? "bg-neo-green" : "bg-neo-pink animate-pulse"
                )} />
                Connection
              </span>
              <NeoBadge
                variant={isConnected ? 'success' : 'error'}
                className={cn(!isConnected && "animate-pulse", "text-[9px] py-0 px-1 h-3")}
              >
                {isConnected ? 'ONLINE' : 'OFFLINE'}
              </NeoBadge>
            </div>

            {/* Run Status */}
            <div className="flex justify-between items-center">
              <span className="text-[9px] font-bold uppercase text-gray-500">
                Run Status
              </span>
              <NeoBadge
                variant={
                  runState === 'RUNNING' ? 'info' :
                    runState === 'COMPLETE' ? 'success' :
                      'neutral'
                }
                className="text-[9px] py-0 px-1 h-3"
              >
                {runState === 'COMPLETE' && 'OK '}
                {runState === 'RUNNING' && '>> '}
                {runBadgeLabel}
              </NeoBadge>
            </div>
          </div>
        </header>

        <div className="flex-1 flex flex-col min-h-0 bg-neo-bg">
          {/* Controls & Players - FIXED (Non-scrolling area to ensure visibility) */}
          <div className="shrink-0 flex flex-col gap-1 p-1 border-b-2 border-black bg-white z-10">
            <GameControls />
            <PlayerPanel />
          </div>

          {/* Scrolling Area for Deeds/Auction which can be long */}
          <div className="flex-1 overflow-y-auto p-1 min-h-0 relative bg-neo-bg">
            <OwnershipPanel />
            {(showAuction || showTrade) && (
              <div className="mt-2 flex flex-col gap-2">
                <AuctionPanel visible={showAuction} />
                <TradeInspectorPanel visible={showTrade} />
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Area: Board (Centered & Scaled) */}
      <main className="flex-1 h-full relative flex items-center justify-center bg-neo-bg p-4 overflow-hidden">
        {/* Background Grid Pattern */}
        <div className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage: 'linear-gradient(#000 2px, transparent 2px), linear-gradient(90deg, #000 2px, transparent 2px)',
            backgroundSize: '40px 40px'
          }}
        />

        <Board spaces={snapshot?.board || []} className="h-full max-h-[95vh] w-auto aspect-square shadow-2xl relative z-10" />
        <DecisionOverlay />
      </main>

      {/* Right Sidebar: Feed */}
      <aside className="w-96 h-full border-l-4 border-black bg-white flex flex-col z-20 shadow-[-8px_0px_0px_0px_rgba(0,0,0,1)]">
        <div className="px-4 py-3 border-b-2 border-neo-bg flex justify-between items-center bg-gray-50">
          <h2 className="text-lg font-black uppercase">Live Feed</h2>
          <div className="text-right leading-none">
            <span className="text-[10px] font-bold block text-gray-500">TURN</span>
            <span className="text-xl font-mono font-black">{snapshot?.turn_index ?? 0}</span>
          </div>
        </div>
        <div className="flex-1 min-h-0 relative">
          <EventFeed />
        </div>
      </aside>

      <Inspector />
    </div>
  );
}

export default App;

const getHighlightIndices = (event: Event): number[] => {
  switch (event.type) {
    case 'PLAYER_MOVED': {
      const indices = [event.payload.to];
      if (event.payload.passed_go) {
        indices.push(GO_INDEX);
      }
      return indices;
    }
    case 'PROPERTY_PURCHASED':
      return [event.payload.space_index];
    case 'RENT_PAID':
      return [event.payload.space_index];
    case 'SENT_TO_JAIL':
      return [JAIL_INDEX];
    default:
      return [];
  }
};
