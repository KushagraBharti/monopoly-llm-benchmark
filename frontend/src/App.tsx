import { useEffect } from 'react';
import { getWsUrl, WsClient } from './net/ws';
import { useGameStore } from './state/store';
import { Board } from './components/board/Board';
import { PlayerPanel } from './components/panels/PlayerPanel';
import { EventFeed } from './components/feed/EventFeed';
import { GameControls } from './components/panels/GameControls';
import { Inspector } from './components/panels/Inspector';
import { NeoBadge } from './components/ui/NeoPrimitive';

function App() {
  const setStatus = useGameStore((state) => state.setStatus);
  const setSnapshot = useGameStore((state) => state.setSnapshot);
  const pushEvent = useGameStore((state) => state.pushEvent);
  const setRun = useGameStore((state) => state.setRun);
  const snapshot = useGameStore((state) => state.snapshot);

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

  return (
    <div className="h-screen w-screen bg-neo-bg text-black font-sans overflow-hidden flex relative">

      {/* Sidebar: Left Panel (Players & Controls) */}
      <aside className="w-80 h-full border-r-4 border-black bg-white flex flex-col p-4 z-20 shadow-neo-lg z-30">
        <header className="mb-6">
          <h1 className="text-4xl font-black uppercase tracking-tighter leading-none">
            Monopoly <br /><span className="text-neo-pink animate-pulse-neon block mt-1 filter drop-shadow-lg">Arena</span>
          </h1>
          <div className="flex gap-2 mt-2">
            <NeoBadge variant="info">v2.0 (Tw4)</NeoBadge>
            <NeoBadge variant="neutral">{snapshot?.run_id ? 'Active' : 'Idle'}</NeoBadge>
          </div>
        </header>

        <div className="flex flex-col gap-4 flex-1 min-h-0">
          <GameControls />
          <PlayerPanel />
        </div>
      </aside>

      {/* Main Area: Board (Centered & Scaled) */}
      <main className="flex-1 h-full relative flex items-center justify-center bg-neo-bg p-8 overflow-hidden">
        {/* Background Grid Pattern */}
        <div className="absolute inset-0 opacity-20 pointer-events-none animate-grid-scroll"
          style={{
            backgroundImage: 'linear-gradient(#000 2px, transparent 2px), linear-gradient(90deg, #000 2px, transparent 2px)',
            backgroundSize: '50px 50px'
          }}
        />

        {/* Floating shapes or artifacts */}
        <div className="absolute top-10 left-10 w-20 h-20 border-4 border-neo-pink opacity-20 animate-float" style={{ animationDelay: '0s' }} />
        <div className="absolute bottom-10 right-10 w-32 h-32 border-4 border-neo-blue opacity-20 animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 left-10 w-16 h-16 bg-neo-yellow opacity-20 rotate-45 animate-float" style={{ animationDelay: '1s' }} />

        <Board spaces={snapshot?.board || []} className="h-full max-h-[95vh] w-auto aspect-square shadow-2xl relative z-10" />
      </main>

      {/* Right Sidebar: Feed (Collapsible logic could be added, fixed for now) */}
      <aside className="w-96 h-full border-l-4 border-black bg-white flex flex-col p-4 z-20 shadow-[-8px_0px_0px_0px_rgba(0,0,0,1)]">
        <div className="mb-2 flex justify-between items-center">
          <h2 className="text-xl font-black uppercase">Live Feed</h2>
          <div className="text-right">
            <span className="text-xs font-bold block">TURN</span>
            <span className="text-2xl font-mono font-black">{snapshot?.turn_index ?? 0}</span>
          </div>
        </div>
        <div className="flex-1 min-h-0">
          <EventFeed />
        </div>
      </aside>

      <Inspector />
    </div>
  );
}

export default App;
