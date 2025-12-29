import { create } from 'zustand'

import type { Event, StateSnapshot } from '@/net/contracts'
import type { ConnectionStatus } from '@/net/ws'

type ConnectionState = {
  status: ConnectionStatus
  lastError?: string
}

export type RunStatusPlayer = {
  player_id: string
  name: string
  model_display_name: string
  openrouter_model_id: string
  reasoning?: {
    effort?: string
  }
}

export type RunStatus = {
  runId: string | null
  turnIndex: number | null
  running: boolean
  paused?: boolean
  connectedClients?: number
  players?: RunStatusPlayer[]
  lastUpdatedAt?: number
}

export type UiState = {
  deedHighlight: number | null
  eventHighlight: number[] | null
  decisionHighlight: number[] | null
}

export type InspectorTab = 'snapshot' | 'last' | 'stream' | 'raw' | 'llm_io'

export type InspectorFocus = {
  decisionId?: string
  eventId?: string
  eventIndex?: number
} | null

export type StoreState = {
  connection: ConnectionState
  runStatus: RunStatus
  snapshot: StateSnapshot | null
  previousSnapshot: StateSnapshot | null
  events: Event[]
  ui: UiState
  inspectorOpen: boolean
  inspectorTab: InspectorTab
  inspectorFocus: InspectorFocus
  llmIoSelectedDecisionId: string | null
  llmIoSelectedAttempt: number | null
  llmIoCompareMode: boolean
  llmIoCompareAttemptA: number | null
  llmIoCompareAttemptB: number | null
  stoppedRunId: string | null
  logResetId: number
  setStatus: (status: ConnectionStatus, error?: string) => void
  setSnapshot: (snapshot: StateSnapshot) => void
  pushEvent: (event: Event) => void
  setRunStatus: (status: Partial<RunStatus>) => void
  setDeedHighlight: (index: number | null) => void
  setEventHighlight: (indices: number[] | null) => void
  setDecisionHighlight: (indices: number[] | null) => void
  setInspectorOpen: (open: boolean) => void
  setInspectorTab: (tab: InspectorTab) => void
  setInspectorFocus: (focus: InspectorFocus) => void
  setLlmIoSelectedDecisionId: (decisionId: string | null) => void
  setLlmIoSelectedAttempt: (attempt: number | null) => void
  setLlmIoCompareMode: (enabled: boolean) => void
  setLlmIoCompareAttempts: (attemptA: number | null, attemptB: number | null) => void
  resetEvents: () => void
  resetLogs: () => void
}

const MAX_EVENTS = 200
// Drop late updates from a stopped run to keep the UI cleared after Stop.
const shouldIgnoreRunUpdate = (
  state: StoreState,
  runId: string | null | undefined
): boolean => {
  if (!runId) return false
  return state.stoppedRunId === runId
}

export const useGameStore = create<StoreState>((set) => ({
  connection: { status: 'connecting' },
  runStatus: {
    runId: null,
    turnIndex: null,
    running: false,
    paused: false,
    connectedClients: 0,
    players: [],
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
  inspectorOpen: false,
  inspectorTab: 'snapshot',
  inspectorFocus: null,
  llmIoSelectedDecisionId: null,
  llmIoSelectedAttempt: null,
  llmIoCompareMode: false,
  llmIoCompareAttemptA: null,
  llmIoCompareAttemptB: null,
  stoppedRunId: null,
  logResetId: 0,
  setStatus: (status, error) =>
    set(() => ({
      connection: { status, lastError: error },
    })),
  setSnapshot: (snapshot) =>
    set((state) => {
      if (shouldIgnoreRunUpdate(state, snapshot.run_id)) {
        return {}
      }
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
      if (shouldIgnoreRunUpdate(state, event.run_id)) {
        return {}
      }
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
    set((state) => {
      const nextRunStatus = {
        ...state.runStatus,
        ...status,
        lastUpdatedAt: Date.now(),
      }
      const nextRunning = nextRunStatus.running
      const nextRunId = nextRunStatus.runId
      return {
        runStatus: nextRunStatus,
        stoppedRunId:
          nextRunning && nextRunId && nextRunId !== state.stoppedRunId ? null : state.stoppedRunId,
      }
    }),
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
  setInspectorOpen: (open) =>
    set(() => ({
      inspectorOpen: open,
    })),
  setInspectorTab: (tab) =>
    set(() => ({
      inspectorTab: tab,
    })),
  setInspectorFocus: (focus) =>
    set(() => ({
      inspectorFocus: focus,
    })),
  setLlmIoSelectedDecisionId: (decisionId) =>
    set(() => ({
      llmIoSelectedDecisionId: decisionId,
    })),
  setLlmIoSelectedAttempt: (attempt) =>
    set(() => ({
      llmIoSelectedAttempt: attempt,
    })),
  setLlmIoCompareMode: (enabled) =>
    set(() => ({
      llmIoCompareMode: enabled,
    })),
  setLlmIoCompareAttempts: (attemptA, attemptB) =>
    set(() => ({
      llmIoCompareAttemptA: attemptA,
      llmIoCompareAttemptB: attemptB,
    })),
  resetEvents: () => set(() => ({ events: [] })),
  resetLogs: () =>
    set((state) => ({
      events: [],
      snapshot: null,
      previousSnapshot: null,
      ui: {
        deedHighlight: null,
        eventHighlight: null,
        decisionHighlight: null,
      },
      inspectorOpen: false,
      inspectorTab: 'snapshot',
      inspectorFocus: null,
      llmIoSelectedDecisionId: null,
      llmIoSelectedAttempt: null,
      llmIoCompareMode: false,
      llmIoCompareAttemptA: null,
      llmIoCompareAttemptB: null,
      stoppedRunId: state.runStatus.runId ?? state.snapshot?.run_id ?? null,
      logResetId: state.logResetId + 1,
    })),
}))
