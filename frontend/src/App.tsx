import { useEffect } from 'react';
import { getWsUrl, WsClient } from './net/ws';
import { useGameStore } from './state/store';
import { Board } from './components/board/Board';
import { PlayerPanel } from './components/panels/PlayerPanel';
import { OwnershipPanel } from './components/panels/OwnershipPanel'; // New
import { EventFeed } from './components/feed/EventFeed';
import { GameControls } from './components/panels/GameControls';
import { Inspector } from './components/panels/Inspector';
import { NeoBadge, cn } from './components/ui/NeoPrimitive';

function App() {
  const setStatus = useGameStore((state) => state.setStatus);
  const setSnapshot = useGameStore((state) => state.setSnapshot);
  const pushEvent = useGameStore((state) => state.pushEvent);
  const setRun = useGameStore((state) => state.setRun);
  const snapshot = useGameStore((state) => state.snapshot);
  const connection = useGameStore((state) => state.connection);

  useEffect(() => {
    const client = new WsClient(getWsUrl(), {
      onHello: (payload) => setRun(payload.run_id, undefined),
      onSnapshot: (payload) => setSnapshot(payload),
      onEvent: (payload) => pushEvent(payload),
      onError: (payload) => setStatus('disconnected', payload.message),
      onStatusChange: (status, error) => setStatus(status, error),
    });
    client.connect();
    return () => client.close();
  }, [pushEvent, setRun, setSnapshot, setStatus]);

  // Status Derivation
  const isConnected = connection.status === 'connected';
  const runStatus = snapshot?.phase === 'GAME_OVER' ? 'Complete' : (snapshot?.run_id ? 'Running' : 'Idle');

  return (
    <div className="h-screen w-screen bg-neo-bg text-black font-sans overflow-hidden flex relative">

      {/* Sidebar: Left Panel (Players & Controls & Ownership) */}
      <aside className="w-80 h-full border-r-4 border-black bg-white flex flex-col z-30 shadow-neo-lg">
        <header className="p-4 border-b-2 border-black bg-gray-50">
          <h1 className="text-3xl font-black uppercase tracking-tighter leading-none mb-2">
            Monopoly <br /><span className="text-neo-pink block">Arena</span>
          </h1>

          <div className="flex flex-col gap-1.5 mt-2">
            {/* Connection Status */}
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-bold uppercase text-gray-500 flex items-center gap-1">
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  isConnected ? "bg-neo-green" : "bg-neo-pink animate-pulse"
                )} />
                Connection
              </span>
              <NeoBadge
                variant={isConnected ? 'success' : 'error'}
                className={cn(!isConnected && "animate-pulse")}
              >
                {isConnected ? 'ONLINE' : 'OFFLINE'}
              </NeoBadge>
            </div>

            {/* Run Status */}
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-bold uppercase text-gray-500">
                Run Status
              </span>
              <NeoBadge
                variant={
                  runStatus === 'Running' ? 'info' :
                    runStatus === 'Complete' ? 'success' :
                      'neutral'
                }
              >
                {runStatus === 'Complete' && '🏆 '}
                {runStatus === 'Running' && '▶ '}
                {runStatus.toUpperCase()}
              </NeoBadge>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto flex flex-col p-2 gap-2">
          {/* Controls at top of scroll area */}
          <GameControls />

          <div className="flex-1 flex flex-col gap-2 min-h-0">
            <PlayerPanel />
            <OwnershipPanel />
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
