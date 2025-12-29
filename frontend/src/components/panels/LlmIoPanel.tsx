import { useEffect, useMemo, useRef, useState } from 'react';
import { useGameStore } from '@/state/store';
import { cn, NeoBadge } from '@/components/ui/NeoPrimitive';
import { getPlayerColor } from '@/domain/monopoly/colors';
import type { DecisionAttempt, DecisionBundle, DecisionSummary } from '@/net/decisions';
import { fetchDecisionBundle, fetchDecisionList } from '@/net/decisions';

type DiffLine = {
  type: 'add' | 'remove' | 'context';
  text: string;
};

type DiffResult = {
  lines: DiffLine[];
  truncated: boolean;
};

const MAX_DIFF_CELLS = 200000;
const COPY_RESET_MS = 1400;

const formatAttemptLabel = (index: number): string => (index <= 0 ? 'Initial' : `Retry ${index}`);

const stableNormalize = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map(stableNormalize);
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) =>
      a.localeCompare(b)
    );
    const next: Record<string, unknown> = {};
    for (const [key, entry] of entries) {
      next[key] = stableNormalize(entry);
    }
    return next;
  }
  return value;
};

const formatJson = (value: unknown): string | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(stableNormalize(value), null, 2);
  } catch {
    return String(value);
  }
};

const diffLines = (leftText: string, rightText: string): DiffResult => {
  const left = leftText.split('\n');
  const right = rightText.split('\n');
  const size = left.length * right.length;
  if (size > MAX_DIFF_CELLS) {
    return { lines: [], truncated: true };
  }
  const dp: number[][] = Array.from({ length: left.length + 1 }, () =>
    Array(right.length + 1).fill(0)
  );
  for (let i = left.length - 1; i >= 0; i -= 1) {
    for (let j = right.length - 1; j >= 0; j -= 1) {
      if (left[i] === right[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }
  const lines: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < left.length && j < right.length) {
    if (left[i] === right[j]) {
      lines.push({ type: 'context', text: left[i] });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      lines.push({ type: 'remove', text: left[i] });
      i += 1;
    } else {
      lines.push({ type: 'add', text: right[j] });
      j += 1;
    }
  }
  while (i < left.length) {
    lines.push({ type: 'remove', text: left[i] });
    i += 1;
  }
  while (j < right.length) {
    lines.push({ type: 'add', text: right[j] });
    j += 1;
  }
  return { lines, truncated: false };
};

const CopyButton = ({
  value,
  label,
  onCopied,
}: {
  value: string | null;
  label: string;
  onCopied: (label: string) => void;
}) => {
  const handleCopy = async () => {
    if (!value) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = value;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      onCopied(`Copied ${label}`);
    } catch {
      onCopied('Copy failed');
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      disabled={!value}
      className={cn(
        'brutal-btn text-[9px] py-0.5 px-2 border-black',
        value ? 'bg-neo-yellow text-black' : 'bg-gray-200 text-gray-400 cursor-not-allowed'
      )}
    >
      Copy
    </button>
  );
};

const ArtifactSection = ({
  title,
  value,
  onCopied,
}: {
  title: string;
  value: string | null;
  onCopied: (label: string) => void;
}) => (
  <div className="border-2 border-black bg-white shadow-neo-sm flex flex-col min-h-[120px]">
    <div className="flex items-center justify-between px-2 py-1 border-b-2 border-black bg-neo-bg">
      <span className="text-[10px] font-black uppercase tracking-wide">{title}</span>
      <CopyButton value={value} label={title} onCopied={onCopied} />
    </div>
    <div className="p-2 text-[11px] font-mono whitespace-pre-wrap overflow-auto">
      {value ? value : <span className="text-gray-400">Artifact unavailable.</span>}
    </div>
  </div>
);

const DiffSection = ({
  title,
  leftValue,
  rightValue,
}: {
  title: string;
  leftValue: string | null;
  rightValue: string | null;
}) => {
  if (!leftValue && !rightValue) {
    return (
      <div className="border-2 border-black bg-white shadow-neo-sm">
        <div className="px-2 py-1 border-b-2 border-black bg-neo-bg text-[10px] font-black uppercase">
          {title}
        </div>
        <div className="p-2 text-[11px] text-gray-400">Artifact unavailable.</div>
      </div>
    );
  }
  if (!leftValue || !rightValue) {
    return (
      <div className="border-2 border-black bg-white shadow-neo-sm">
        <div className="px-2 py-1 border-b-2 border-black bg-neo-bg text-[10px] font-black uppercase">
          {title}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2 text-[11px] font-mono">
          <div className="border border-black/10 p-2 bg-gray-50 whitespace-pre-wrap">
            {leftValue ?? 'Missing'}
          </div>
          <div className="border border-black/10 p-2 bg-gray-50 whitespace-pre-wrap">
            {rightValue ?? 'Missing'}
          </div>
        </div>
      </div>
    );
  }

  const diff = diffLines(leftValue, rightValue);
  if (diff.truncated) {
    return (
      <div className="border-2 border-black bg-white shadow-neo-sm">
        <div className="px-2 py-1 border-b-2 border-black bg-neo-bg text-[10px] font-black uppercase">
          {title}
        </div>
        <div className="p-2 text-[11px] text-gray-500">
          Diff too large to render. Showing raw side by side.
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2 text-[11px] font-mono">
          <div className="border border-black/10 p-2 bg-gray-50 whitespace-pre-wrap">{leftValue}</div>
          <div className="border border-black/10 p-2 bg-gray-50 whitespace-pre-wrap">{rightValue}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="border-2 border-black bg-white shadow-neo-sm">
      <div className="px-2 py-1 border-b-2 border-black bg-neo-bg text-[10px] font-black uppercase">
        {title}
      </div>
      <div className="p-2 text-[11px] font-mono whitespace-pre-wrap max-h-[240px] overflow-auto">
        {diff.lines.map((line, idx) => (
          <div
            key={`${title}-${idx}`}
            className={cn(
              'flex gap-2',
              line.type === 'add' && 'text-neo-green',
              line.type === 'remove' && 'text-neo-pink',
              line.type === 'context' && 'text-gray-600'
            )}
          >
            <span className="w-4 shrink-0">{line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}</span>
            <span className="flex-1">{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const buildAttemptMap = (attempts: DecisionAttempt[]) =>
  new Map(attempts.map((attempt) => [attempt.attempt_index, attempt]));

const getAttemptLabel = (attempt: DecisionAttempt | undefined) =>
  attempt ? formatAttemptLabel(attempt.attempt_index) : 'Unknown';

const normalizeErrors = (errors: string[] | null | undefined): string | null => {
  if (!errors || errors.length === 0) return null;
  return errors.join('\n');
};

export const LlmIoPanel = () => {
  const runId = useGameStore((state) => state.runStatus.runId);
  const players = useGameStore((state) => state.runStatus.players ?? []);
  const selectedDecisionId = useGameStore((state) => state.llmIoSelectedDecisionId);
  const selectedAttempt = useGameStore((state) => state.llmIoSelectedAttempt);
  const compareMode = useGameStore((state) => state.llmIoCompareMode);
  const compareAttemptA = useGameStore((state) => state.llmIoCompareAttemptA);
  const compareAttemptB = useGameStore((state) => state.llmIoCompareAttemptB);
  const setSelectedDecisionId = useGameStore((state) => state.setLlmIoSelectedDecisionId);
  const setSelectedAttempt = useGameStore((state) => state.setLlmIoSelectedAttempt);
  const setCompareMode = useGameStore((state) => state.setLlmIoCompareMode);
  const setCompareAttempts = useGameStore((state) => state.setLlmIoCompareAttempts);

  const [decisions, setDecisions] = useState<DecisionSummary[]>([]);
  const [bundle, setBundle] = useState<DecisionBundle | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [bundleError, setBundleError] = useState<string | null>(null);
  const [loadingDecisions, setLoadingDecisions] = useState(false);
  const [loadingBundle, setLoadingBundle] = useState(false);
  const [search, setSearch] = useState('');
  const [copyNotice, setCopyNotice] = useState<string | null>(null);
  const noticeTimerRef = useRef<number | null>(null);
  const selectedDecisionRef = useRef<string | null>(selectedDecisionId);

  const playerNames = useMemo(() => {
    const map = new Map<string, string>();
    players.forEach((player) => {
      map.set(player.player_id, player.name);
    });
    return map;
  }, [players]);

  useEffect(() => {
    selectedDecisionRef.current = selectedDecisionId;
  }, [selectedDecisionId]);

  useEffect(() => {
    if (!runId) {
      setDecisions([]);
      setSelectedDecisionId(null);
      return;
    }
    let active = true;
    setLoadingDecisions(true);
    setDecisionError(null);
    fetchDecisionList(runId, 300)
      .then((data) => {
        if (!active) return;
        setDecisions(data);
        if (!data.length) {
          setSelectedDecisionId(null);
          return;
        }
        const currentSelected = selectedDecisionRef.current;
        if (!currentSelected || !data.some((item) => item.decision_id === currentSelected)) {
          setSelectedDecisionId(data[data.length - 1].decision_id);
        }
      })
      .catch((err) => {
        if (!active) return;
        setDecisionError(err instanceof Error ? err.message : 'Failed to load decisions');
        setDecisions([]);
      })
      .finally(() => {
        if (!active) return;
        setLoadingDecisions(false);
      });
    return () => {
      active = false;
    };
  }, [runId, setSelectedDecisionId]);

  useEffect(() => {
    if (!runId || !selectedDecisionId) {
      setBundle(null);
      return;
    }
    let active = true;
    setLoadingBundle(true);
    setBundleError(null);
    fetchDecisionBundle(runId, selectedDecisionId)
      .then((data) => {
        if (!active) return;
        setBundle(data);
      })
      .catch((err) => {
        if (!active) return;
        setBundleError(err instanceof Error ? err.message : 'Failed to load decision bundle');
        setBundle(null);
      })
      .finally(() => {
        if (!active) return;
        setLoadingBundle(false);
      });
    return () => {
      active = false;
    };
  }, [runId, selectedDecisionId]);

  useEffect(() => {
    if (!bundle) return;
    const attemptIndices = bundle.attempts.map((attempt) => attempt.attempt_index);
    if (!attemptIndices.length) return;
    const latest = attemptIndices[attemptIndices.length - 1];
    if (selectedAttempt === null || !attemptIndices.includes(selectedAttempt)) {
      setSelectedAttempt(latest);
    }
    if (attemptIndices.length < 2 && compareMode) {
      setCompareMode(false);
      return;
    }
    if (!compareMode) return;
    const nextA = compareAttemptA !== null && attemptIndices.includes(compareAttemptA) ? compareAttemptA : attemptIndices[0];
    const nextB = compareAttemptB !== null && attemptIndices.includes(compareAttemptB) ? compareAttemptB : latest;
    if (nextA !== compareAttemptA || nextB !== compareAttemptB) {
      setCompareAttempts(nextA, nextB);
    }
  }, [
    bundle,
    selectedAttempt,
    setSelectedAttempt,
    compareMode,
    compareAttemptA,
    compareAttemptB,
    setCompareMode,
    setCompareAttempts,
  ]);

  useEffect(() => {
    if (!copyNotice) return;
    if (noticeTimerRef.current) {
      window.clearTimeout(noticeTimerRef.current);
    }
    noticeTimerRef.current = window.setTimeout(() => {
      setCopyNotice(null);
      noticeTimerRef.current = null;
    }, COPY_RESET_MS);
    return () => {
      if (noticeTimerRef.current) {
        window.clearTimeout(noticeTimerRef.current);
        noticeTimerRef.current = null;
      }
    };
  }, [copyNotice]);

  const attemptMap = useMemo(() => buildAttemptMap(bundle?.attempts ?? []), [bundle]);
  const attemptIndices = useMemo(
    () => (bundle?.attempts ?? []).map((attempt) => attempt.attempt_index),
    [bundle]
  );
  const latestAttempt = attemptIndices.length ? attemptIndices[attemptIndices.length - 1] : null;
  const selectedAttemptItem = selectedAttempt !== null ? attemptMap.get(selectedAttempt) : undefined;

  const searchLower = search.trim().toLowerCase();
  const filteredDecisions = useMemo(() => {
    if (!searchLower) return decisions;
    return decisions.filter((entry) => {
      const playerName = entry.player_id ? playerNames.get(entry.player_id) ?? entry.player_id : '';
      const haystack = `${entry.decision_id} ${entry.decision_type ?? ''} ${playerName} ${entry.turn_index ?? ''}`.toLowerCase();
      return haystack.includes(searchLower);
    });
  }, [decisions, searchLower, playerNames]);

  const groupedDecisions = useMemo(() => {
    const groups = new Map<number | null, DecisionSummary[]>();
    filteredDecisions.forEach((entry) => {
      const key = entry.turn_index ?? null;
      const list = groups.get(key) ?? [];
      list.push(entry);
      groups.set(key, list);
    });
    const ordered = Array.from(groups.entries()).sort(([a], [b]) => {
      if (a === null) return 1;
      if (b === null) return -1;
      return a - b;
    });
    return ordered.map(([turnIndex, entries]) => ({ turnIndex, entries }));
  }, [filteredDecisions]);

  const renderDecisionItem = (entry: DecisionSummary) => {
    const isSelected = entry.decision_id === selectedDecisionId;
    const playerId = entry.player_id ?? 'unknown';
    const playerName = playerNames.get(playerId) ?? playerId;
    const decisionType = entry.decision_type ?? 'UNKNOWN';
    const suffix = entry.decision_id.slice(-6);
    return (
      <button
        key={entry.decision_id}
        type="button"
        onClick={() => setSelectedDecisionId(entry.decision_id)}
        className={cn(
          'border-2 border-black p-2 text-left bg-white shadow-neo-sm transition-all',
          isSelected && 'bg-neo-yellow/30'
        )}
      >
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-sm border border-black"
            style={{ backgroundColor: getPlayerColor(playerId) }}
          />
          <span className="text-[10px] font-bold uppercase">{playerName}</span>
          <span className="text-[9px] font-mono text-gray-500">#{suffix}</span>
        </div>
        <div className="text-[10px] uppercase font-black mt-1">{decisionType}</div>
        <div className="flex flex-wrap gap-1 mt-1">
          {entry.retry_used && (
            <NeoBadge variant="warning" className="text-[8px] py-0 px-1">
              RETRY
            </NeoBadge>
          )}
          {entry.fallback_used && (
            <NeoBadge variant="error" className="text-[8px] py-0 px-1">
              FALLBACK
            </NeoBadge>
          )}
        </div>
      </button>
    );
  };

  const leftPayload = formatJson(selectedAttemptItem?.user_payload);
  const leftTools = formatJson(selectedAttemptItem?.tools);
  const leftSystem = selectedAttemptItem?.system_prompt ?? null;
  const rightResponse = formatJson(selectedAttemptItem?.response);
  const rightParsed = formatJson(selectedAttemptItem?.parsed_tool_call);
  const rightErrors = normalizeErrors(selectedAttemptItem?.validation_errors ?? null);
  const rightToolAction = formatJson(selectedAttemptItem?.tool_action);
  const finalAction = formatJson(bundle?.final_action ?? null);

  const attemptA = compareAttemptA !== null ? attemptMap.get(compareAttemptA) : undefined;
  const attemptB = compareAttemptB !== null ? attemptMap.get(compareAttemptB) : undefined;

  if (!runId) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-500">
        No active run. Start a run to inspect decisions.
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {copyNotice && (
        <div className="absolute top-4 right-6 bg-black text-white text-[10px] font-bold px-3 py-1 shadow-neo">
          {copyNotice}
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)_minmax(0,1fr)] gap-3 h-full min-h-0">
        <div className="border-2 border-black bg-white shadow-neo-sm flex flex-col min-h-0">
          <div className="px-2 py-2 border-b-2 border-black bg-neo-bg">
            <div className="text-[10px] font-black uppercase tracking-wider">Decisions</div>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search..."
              className="mt-2 w-full border-2 border-black px-2 py-1 text-[11px] font-mono bg-white"
            />
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2 brutal-scroll">
            {loadingDecisions && <div className="text-[11px] text-gray-500">Loading decisions...</div>}
            {decisionError && <div className="text-[11px] text-neo-pink">{decisionError}</div>}
            {!loadingDecisions && !decisionError && groupedDecisions.length === 0 && (
              <div className="text-[11px] text-gray-400">No decisions yet.</div>
            )}
            {groupedDecisions.map((group) => (
              <div key={`turn-${group.turnIndex ?? 'unknown'}`} className="space-y-2">
                <div className="text-[9px] font-bold uppercase text-gray-500">
                  {group.turnIndex === null ? 'Unknown Turn' : `Turn ${group.turnIndex}`}
                </div>
                <div className="space-y-2">{group.entries.map(renderDecisionItem)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="col-span-1 lg:col-span-2 flex flex-col min-h-0 gap-3">
          <div className="border-2 border-black bg-white shadow-neo-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 px-2 py-2 border-b-2 border-black bg-neo-bg">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase">LLM I/O</span>
                {bundle?.summary?.decision_type && (
                  <NeoBadge variant="neutral" className="text-[8px] py-0 px-1">
                    {bundle.summary.decision_type}
                  </NeoBadge>
                )}
                {bundle?.retry_used && (
                  <NeoBadge variant="warning" className="text-[8px] py-0 px-1">
                    RETRY
                  </NeoBadge>
                )}
                {bundle?.fallback_used && (
                  <NeoBadge variant="error" className="text-[8px] py-0 px-1">
                    FALLBACK
                  </NeoBadge>
                )}
              </div>
              <div className="flex items-center gap-2">
                {attemptIndices.length > 1 && !compareMode && (
                  <label className="text-[9px] font-bold uppercase flex items-center gap-1">
                    Attempt
                    <select
                      className="border-2 border-black px-2 py-1 text-[10px] font-mono"
                      value={selectedAttempt ?? latestAttempt ?? ''}
                      onChange={(event) => setSelectedAttempt(Number(event.target.value))}
                    >
                      {attemptIndices.map((index) => (
                        <option key={`attempt-${index}`} value={index}>
                          {formatAttemptLabel(index)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <button
                  type="button"
                  onClick={() => setCompareMode(!compareMode)}
                  disabled={attemptIndices.length < 2}
                  className={cn(
                    'brutal-btn text-[9px] py-1 px-2 border-black',
                    compareMode ? 'bg-black text-white' : 'bg-white text-black',
                    attemptIndices.length < 2 && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  Compare
                </button>
              </div>
            </div>
            {loadingBundle && <div className="p-3 text-[11px] text-gray-500">Loading decision...</div>}
            {bundleError && <div className="p-3 text-[11px] text-neo-pink">{bundleError}</div>}
          </div>

          {!loadingBundle && !bundleError && !bundle && (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-500">
              Select a decision to inspect.
            </div>
          )}

          {bundle && !compareMode && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 flex-1 min-h-0">
              <div className="flex flex-col gap-3 min-h-0 overflow-y-auto pr-1 brutal-scroll">
                <ArtifactSection title="System Prompt" value={leftSystem} onCopied={setCopyNotice} />
                <ArtifactSection title="Input Payload" value={leftPayload} onCopied={setCopyNotice} />
                <ArtifactSection title="Tools Schema" value={leftTools} onCopied={setCopyNotice} />
              </div>
              <div className="flex flex-col gap-3 min-h-0 overflow-y-auto pr-1 brutal-scroll">
                <ArtifactSection title="Raw Response" value={rightResponse} onCopied={setCopyNotice} />
                <ArtifactSection title="Parsed Tool Call" value={rightParsed} onCopied={setCopyNotice} />
                <ArtifactSection title="Validation Errors" value={rightErrors} onCopied={setCopyNotice} />
                <ArtifactSection title="Tool Action" value={rightToolAction} onCopied={setCopyNotice} />
                <ArtifactSection title="Final Action" value={finalAction} onCopied={setCopyNotice} />
              </div>
            </div>
          )}

          {bundle && compareMode && (
            <div className="flex flex-col gap-3 flex-1 min-h-0 overflow-y-auto brutal-scroll pr-1">
              <div className="border-2 border-black bg-white shadow-neo-sm">
                <div className="flex flex-wrap items-center gap-3 px-2 py-2 border-b-2 border-black bg-neo-bg">
                  <label className="text-[9px] font-bold uppercase flex items-center gap-2">
                    Attempt A
                    <select
                      className="border-2 border-black px-2 py-1 text-[10px] font-mono"
                      value={compareAttemptA ?? ''}
                      onChange={(event) => setCompareAttempts(Number(event.target.value), compareAttemptB)}
                    >
                      {attemptIndices.map((index) => (
                        <option key={`compare-a-${index}`} value={index}>
                          {formatAttemptLabel(index)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-[9px] font-bold uppercase flex items-center gap-2">
                    Attempt B
                    <select
                      className="border-2 border-black px-2 py-1 text-[10px] font-mono"
                      value={compareAttemptB ?? ''}
                      onChange={(event) => setCompareAttempts(compareAttemptA, Number(event.target.value))}
                    >
                      {attemptIndices.map((index) => (
                        <option key={`compare-b-${index}`} value={index}>
                          {formatAttemptLabel(index)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="text-[9px] font-mono text-gray-500">
                    {getAttemptLabel(attemptA)} vs {getAttemptLabel(attemptB)}
                  </div>
                </div>
              </div>
              <DiffSection
                title="Input Payload Diff"
                leftValue={formatJson(attemptA?.user_payload ?? null)}
                rightValue={formatJson(attemptB?.user_payload ?? null)}
              />
              <DiffSection
                title="Raw Response Diff"
                leftValue={formatJson(attemptA?.response ?? null)}
                rightValue={formatJson(attemptB?.response ?? null)}
              />
              <DiffSection
                title="Parsed Tool Call Diff"
                leftValue={formatJson(attemptA?.parsed_tool_call ?? null)}
                rightValue={formatJson(attemptB?.parsed_tool_call ?? null)}
              />
              <DiffSection
                title="Validation Errors Diff"
                leftValue={normalizeErrors(attemptA?.validation_errors ?? null)}
                rightValue={normalizeErrors(attemptB?.validation_errors ?? null)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
