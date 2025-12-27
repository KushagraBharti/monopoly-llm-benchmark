import { create } from 'zustand'

import type { Event, StateSnapshot } from '../net/contracts'
import type { ConnectionStatus } from '../net/ws'

type ConnectionState = {
  status: ConnectionStatus
  lastError?: string
}

type RunStatus = {
  runId: string | null
  turnIndex: number | null
  running: boolean
  connectedClients?: number
  lastUpdatedAt?: number
}

type UiState = {
  deedHighlight: number | null
  eventHighlight: number[] | null
  decisionHighlight: number[] | null
}

type StoreState = {
  connection: ConnectionState
  runStatus: RunStatus
  snapshot: StateSnapshot | null
  previousSnapshot: StateSnapshot | null
  events: Event[]
  ui: UiState
  setStatus: (status: ConnectionStatus, error?: string) => void
  setSnapshot: (snapshot: StateSnapshot) => void
  pushEvent: (event: Event) => void
  setRunStatus: (status: Partial<RunStatus>) => void
  setDeedHighlight: (index: number | null) => void
  setEventHighlight: (indices: number[] | null) => void
  setDecisionHighlight: (indices: number[] | null) => void
  resetEvents: () => void
}

const MAX_EVENTS = 200

export const useGameStore = create<StoreState>((set) => ({
  connection: { status: 'connecting' },
  runStatus: {
    runId: null,
    turnIndex: null,
    running: false,
    connectedClients: 0,
    lastUpdatedAt: undefined,
  },
  snapshot: null,
  previousSnapshot: null,
  events: [],
  ui: {
    deedHighlight: null,
    eventHighlight: null,
    decisionHighlight: null,
  },
  setStatus: (status, error) =>
    set(() => ({
      connection: { status, lastError: error },
    })),
  setSnapshot: (snapshot) =>
    set((state) => {
      const prevRunId = state.snapshot?.run_id
      const prevTurn = state.snapshot?.turn_index ?? null
      const isNewRun = prevRunId !== undefined && prevRunId !== snapshot.run_id
      const isRestart =
        prevRunId === snapshot.run_id && prevTurn !== null && prevTurn > 0 && snapshot.turn_index === 0
      const shouldReset = (isNewRun || isRestart) && snapshot.run_id !== 'idle'
      return {
        previousSnapshot: shouldReset ? null : state.snapshot,
        snapshot,
        events: shouldReset ? [] : state.events,
      }
    }),
  pushEvent: (event) =>
    set((state) => {
      const isGameStart = event.type === 'GAME_STARTED'
      const nextEvents = isGameStart ? [event] : [event, ...state.events]
      if (nextEvents.length > MAX_EVENTS) {
        nextEvents.pop()
      }
      return {
        events: nextEvents,
      }
    }),
  setRunStatus: (status) =>
    set((state) => ({
      runStatus: {
        ...state.runStatus,
        ...status,
        lastUpdatedAt: Date.now(),
      },
    })),
  setDeedHighlight: (index) =>
    set((state) => ({
      ui: { ...state.ui, deedHighlight: index },
    })),
  setEventHighlight: (indices) =>
    set((state) => ({
      ui: { ...state.ui, eventHighlight: indices },
    })),
  setDecisionHighlight: (indices) =>
    set((state) => ({
      ui: { ...state.ui, decisionHighlight: indices },
    })),
  resetEvents: () => set(() => ({ events: [] })),
}))
