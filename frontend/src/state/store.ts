import { create } from 'zustand'

import type { Event, StateSnapshot } from '../net/contracts'
import type { ConnectionStatus } from '../net/ws'

type ConnectionState = {
  status: ConnectionStatus
  lastError?: string
}

type RunState = {
  runId?: string | null
  turnIndex?: number | null
}

type StoreState = {
  connection: ConnectionState
  run: RunState
  snapshot: StateSnapshot | null
  events: Event[]
  setStatus: (status: ConnectionStatus, error?: string) => void
  setSnapshot: (snapshot: StateSnapshot) => void
  pushEvent: (event: Event) => void
  setRun: (runId?: string | null, turnIndex?: number | null) => void
  resetEvents: () => void
}

const MAX_EVENTS = 200

export const useGameStore = create<StoreState>((set, get) => ({
  connection: { status: 'connecting' },
  run: {},
  snapshot: null,
  events: [],
  setStatus: (status, error) =>
    set(() => ({
      connection: { status, lastError: error },
    })),
  setSnapshot: (snapshot) =>
    set((state) => {
      const isNewRun = state.run.runId && state.run.runId !== snapshot.run_id
      return {
        snapshot,
        run: { runId: snapshot.run_id, turnIndex: snapshot.turn_index },
        events: isNewRun ? [] : state.events,
      }
    }),
  pushEvent: (event) =>
    set((state) => {
      const nextEvents = [event, ...state.events]
      if (nextEvents.length > MAX_EVENTS) {
        nextEvents.pop()
      }
      return {
        events: nextEvents,
        run: { runId: state.run.runId ?? event.run_id, turnIndex: event.turn_index },
      }
    }),
  setRun: (runId, turnIndex) =>
    set(() => ({
      run: { runId, turnIndex },
    })),
  resetEvents: () => set(() => ({ events: [] })),
}))
