"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/store/workspaceStore";
import { Textarea } from "@/components/ui/textarea";
import {
  verifyClaim,
  getRecentVerifications,
  type ClaimVerifyResponse,
  type ScoredEvidenceItem,
  type ClaimVerifyRunItem,
} from "@/lib/api/tools";
import { useWSEvent } from "@/lib/ws/WebSocketProvider";
import { Loader2, CheckCircle, XCircle, MinusCircle, ChevronDown, ChevronUp, Users } from "lucide-react";

const EXAMPLE_CLAIMS = [
  "Coffee reduces anxiety in adults.",
  "Vitamin D supplementation prevents respiratory infections.",
  "The intervention significantly improved outcomes.",
];

const STORAGE_KEY_PREFIX = "claim-verify";

function getStorageKey(workspaceId: string | undefined): string {
  return `${STORAGE_KEY_PREFIX}-${workspaceId ?? "default"}`;
}

function loadPersisted(workspaceId: string | undefined): { claim: string; result: ClaimVerifyResponse } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(getStorageKey(workspaceId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { claim?: string; result?: ClaimVerifyResponse };
    if (parsed?.result) return { claim: parsed.claim ?? "", result: parsed.result };
  } catch {
    // ignore
  }
  return null;
}

function savePersisted(workspaceId: string | undefined, claim: string, result: ClaimVerifyResponse): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(
      getStorageKey(workspaceId),
      JSON.stringify({ claim, result })
    );
  } catch {
    // ignore
  }
}

/** Group scored evidence by paper (one entry per document). */
function groupEvidenceByPaper(items: ScoredEvidenceItem[]): { paperId: string; paperTitle: string; chunks: ScoredEvidenceItem[] }[] {
  const byPaper = new Map<string, ScoredEvidenceItem[]>();
  const titleByPaper = new Map<string, string>();
  for (const item of items) {
    const id = item.paper_id || item.paper_title || "unknown";
    if (!byPaper.has(id)) {
      byPaper.set(id, []);
      titleByPaper.set(id, item.paper_title || "Unknown");
    }
    byPaper.get(id)!.push(item);
    if (item.paper_title) titleByPaper.set(id, item.paper_title);
  }
  return Array.from(byPaper.entries()).map(([paperId, chunks]) => ({
    paperId,
    paperTitle: titleByPaper.get(paperId) || "Unknown",
    chunks,
  }));
}

function EvidenceChunkRow({ item }: { item: ScoredEvidenceItem }) {
  const [open, setOpen] = useState(false);
  const cls = item.classification?.classification ?? "NEUTRAL";
  const isSupport = cls === "SUPPORT";
  const isContradict = cls === "CONTRADICT";
  return (
    <div className="rounded-lg border border-border/60 bg-muted/40 overflow-hidden">
      <button
        type="button"
        className="w-full text-left px-3 py-2.5 flex items-center gap-3 hover:bg-muted/50 transition-colors text-sm"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="flex items-center gap-2 shrink-0">
          {isSupport && <CheckCircle className="h-4 w-4 text-green-600" />}
          {isContradict && <XCircle className="h-4 w-4 text-red-600" />}
          {!isSupport && !isContradict && <MinusCircle className="h-4 w-4 text-muted-foreground" />}
          <span className={`text-xs font-medium ${isSupport ? "text-green-700" : isContradict ? "text-red-700" : "text-muted-foreground"}`}>
            {cls}
          </span>
        </span>
        <span className="text-muted-foreground text-xs truncate flex-1">Page {item.page_number}</span>
        <span className="text-xs text-muted-foreground tabular-nums">{(item.evidence_score ?? 0).toFixed(2)}</span>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-0 border-t border-border/40 bg-muted/30">
          <div className="py-2 space-y-1.5 text-xs text-muted-foreground">
            <div className="flex flex-wrap gap-x-4 gap-y-0.5">
              <span>Strength <strong className="text-foreground font-normal">{evidenceStrengthWord(item.evidence_score ?? 0)}</strong></span>
              <span>Relevance <strong className="text-foreground font-normal">{(item.similarity_score ?? 0).toFixed(1)}</strong></span>
              {item.classification?.confidence != null && (
                <span>Certainty <strong className="text-foreground font-normal">{(item.classification.confidence * 100).toFixed(0)}%</strong></span>
              )}
            </div>
            {item.score_components && Object.keys(item.score_components).length > 0 && (
              <div className="flex flex-wrap gap-x-3 pt-1 border-t border-border/40">
                {Object.entries(item.score_components)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .slice(0, 5)
                  .map(([k, v]) => (
                    <span key={k}>{COMPONENT_LABELS[k] ?? k.replace(/_/g, " ")} <strong className="text-foreground font-normal">{Number(v).toFixed(1)}</strong></span>
                  ))}
              </div>
            )}
          </div>
          <p className="text-xs text-muted-foreground mb-2">{item.classification?.reason}</p>
          <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{item.text}</p>
        </div>
      )}
    </div>
  );
}

function PaperEvidenceCard({
  paperTitle,
  chunks,
}: {
  paperTitle: string;
  chunks: ScoredEvidenceItem[];
}) {
  const [showChunks, setShowChunks] = useState(false);
  const support = chunks.filter((c) => (c.classification?.classification ?? "") === "SUPPORT").length;
  const contradict = chunks.filter((c) => (c.classification?.classification ?? "") === "CONTRADICT").length;
  const neutral = chunks.filter((c) => (c.classification?.classification ?? "") === "NEUTRAL").length;
  const avgScore = chunks.length ? chunks.reduce((s, c) => s + (c.evidence_score ?? 0), 0) / chunks.length : 0;
  const verdict = contradict > 0 ? (support > contradict ? "Mostly supports" : "Mostly contradicts") : support > 0 ? "Supports" : "Neutral";

  return (
    <div className="rounded-lg border border-border/60 bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-sm">{paperTitle}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {verdict === "Supports" && <span className="text-green-600">{verdict}</span>}
            {verdict === "Mostly contradicts" && <span className="text-red-600">{verdict}</span>}
            {!["Supports", "Mostly contradicts"].includes(verdict) && <span>{verdict}</span>}
            {" · "}{support} support, {contradict} contradict, {neutral} neutral · {evidenceStrengthWord(avgScore)}
          </p>
        </div>
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-foreground shrink-0 flex items-center gap-1"
          onClick={() => setShowChunks((v) => !v)}
        >
          {showChunks ? "Hide details" : "Show details"}
          {showChunks ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>
      {showChunks && (
        <div className="mt-3 pt-3 border-t border-border/40 space-y-2">
          {chunks.map((item, i) => (
            <EvidenceChunkRow key={i} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

/** Human-readable label for evidence score (0–1). */
function evidenceStrengthWord(score: number): string {
  if (score >= 0.7) return "Strong";
  if (score >= 0.5) return "Moderate";
  if (score >= 0.3) return "Modest";
  return "Weak";
}

/** One plain-language sentence for the overall result. */
function bottomLineSentence(result: ClaimVerifyResponse): string {
  const { confidence_label, support_count, contradict_count, neutral_count, evidence_count, guardrail_triggered } = result;
  if (guardrail_triggered?.includes("Insufficient")) {
    return "There isn’t enough evidence in your documents to verify this claim.";
  }
  if (guardrail_triggered?.includes("No evidence")) {
    return "No relevant passages were found for this claim.";
  }
  if (confidence_label === "Contradicted") {
    return `Across ${evidence_count} passage${evidence_count !== 1 ? "s" : ""}, the evidence leans against the claim.`;
  }
  if (support_count === 0 && contradict_count === 0) {
    return `We found ${evidence_count} relevant passage${evidence_count !== 1 ? "s" : ""}, but none clearly support or contradict the claim.`;
  }
  if (support_count > 0 && contradict_count === 0) {
    return `Based on ${evidence_count} passage${evidence_count !== 1 ? "s" : ""}, ${support_count} support the claim${neutral_count > 0 ? ` and ${neutral_count} are neutral` : ""}.`;
  }
  if (contradict_count > 0 && support_count === 0) {
    return `Among ${evidence_count} passage${evidence_count !== 1 ? "s" : ""}, ${contradict_count} contradict the claim${neutral_count > 0 ? ` and ${neutral_count} are neutral` : ""}.`;
  }
  return `Evidence is mixed: ${support_count} supporting, ${contradict_count} contradicting${neutral_count > 0 ? `, ${neutral_count} neutral` : ""} across ${evidence_count} passages.`;
}

/** Human label for score component keys. */
const COMPONENT_LABELS: Record<string, string> = {
  semantic_similarity: "Relevance to claim",
  study_type_weight: "Study quality",
  citation_score: "Source impact (citations)",
  recency_score: "Recency",
  source_credibility: "Source reputation",
};

function formatRunTime(createdAt: string): string {
  try {
    const d = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    if (diffMs < 60000) return "just now";
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return "";
  }
}

function RecentRunRow({
  run,
  currentUserId,
  expanded,
  onToggle,
}: {
  run: ClaimVerifyRunItem;
  currentUserId: string | undefined;
  expanded: boolean;
  onToggle: () => void;
}) {
  const isMe = currentUserId && run.user_id === currentUserId;
  const r = run.result;
  const labelColor =
    r.confidence_label === "Strong" ? "text-green-600" :
    r.confidence_label === "Moderate" ? "text-blue-600" :
    r.confidence_label === "Contradicted" ? "text-red-600" : "text-muted-foreground";
  return (
    <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
      <button
        type="button"
        className="w-full text-left px-4 py-3 flex flex-wrap items-center gap-3 hover:bg-muted/40 transition-colors"
        onClick={onToggle}
      >
        <span className="text-sm truncate flex-1 min-w-0">{run.claim}</span>
        <span className="text-xs text-muted-foreground shrink-0">
          {isMe ? "You" : run.user_name} · {formatRunTime(run.created_at)}
        </span>
        <span className={`text-xs font-medium shrink-0 ${labelColor}`}>{r.confidence_label}</span>
        {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-border/40">
          <ResultView result={r} />
        </div>
      )}
    </div>
  );
}

function ResultView({ result }: { result: ClaimVerifyResponse }) {
  const label = result.confidence_label;
  const isStrong = label === "Strong";
  const isModerate = label === "Moderate";
  const isWeak = label === "Weak";
  const isContradicted = label === "Contradicted" || (result.guardrail_triggered && result.guardrail_triggered.includes("Contradict"));
  const isInsufficient = label === "Insufficient Evidence" || (result.guardrail_triggered && result.guardrail_triggered.includes("Insufficient"));

  const hasEvidence = result.scored_evidence && result.scored_evidence.length > 0;
  const byPaper = hasEvidence ? groupEvidenceByPaper(result.scored_evidence) : [];

  const labelColor =
    isStrong ? "text-green-600" :
    isModerate ? "text-blue-600" :
    isWeak ? "text-amber-600" :
    isContradicted ? "text-red-600" :
    "text-muted-foreground";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Result */}
      <div className="min-w-0">
        <div className="rounded-lg border border-border/60 bg-card p-5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Result</p>
          <p className={`mt-1 text-xl font-semibold ${labelColor}`}>{result.confidence_label}</p>
          <p className="mt-2 text-sm text-muted-foreground">
            {(result.confidence_score * 100).toFixed(0)}% confidence · {result.support_count} support, {result.contradict_count} contradict, {result.neutral_count} neutral
          </p>
          {result.evidence_strength && (
            <p className="mt-1.5 text-xs text-muted-foreground">{result.evidence_strength}</p>
          )}
          {result.guardrail_triggered && (
            <p className="mt-2 text-xs text-amber-600">{result.guardrail_triggered}</p>
          )}
          <p className="mt-4 pt-4 border-t border-border/40 text-sm text-muted-foreground leading-relaxed">
            {bottomLineSentence(result)}
          </p>
        </div>
      </div>

      {/* Right: Evidence by paper */}
      <div className="min-w-0 flex flex-col">
        {hasEvidence ? (
          <>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Evidence by paper ({byPaper.length})
            </p>
            <div className="space-y-3 overflow-auto min-h-0">
              {byPaper.map(({ paperId, paperTitle, chunks }) => (
                <PaperEvidenceCard key={paperId} paperTitle={paperTitle} chunks={chunks} />
              ))}
            </div>
          </>
        ) : (
          <div className="rounded-lg border border-border/60 bg-card p-6 text-sm text-muted-foreground text-center">
            No evidence to show.
          </div>
        )}
      </div>
    </div>
  );
}

function getCurrentUserId(): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = localStorage.getItem("auth_user");
    if (!raw) return undefined;
    const user = JSON.parse(raw) as { user_id?: string };
    return user?.user_id;
  } catch {
    return undefined;
  }
}

export default function ClaimVerifyPage() {
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id;
  const currentUserId = getCurrentUserId();

  const [claim, setClaim] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClaimVerifyResponse | null>(null);
  const [recentRuns, setRecentRuns] = useState<ClaimVerifyRunItem[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(false);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  const fetchRecent = useCallback(async () => {
    if (!workspaceId) return;
    setLoadingRecent(true);
    try {
      const res = await getRecentVerifications(30);
      setRecentRuns(res.runs);
    } catch {
      setRecentRuns([]);
    } finally {
      setLoadingRecent(false);
    }
  }, [workspaceId]);

  // Load shared history when workspace is set
  useEffect(() => {
    fetchRecent();
  }, [fetchRecent]);

  // When a collaborator runs a verification, we receive it via WebSocket
  useWSEvent("claim_verify_result", (event) => {
    const p = event.payload as {
      user_id?: string;
      user_name?: string;
      claim?: string;
      result?: ClaimVerifyResponse;
      created_at?: string;
    } | undefined;
    if (!p?.result) return;
    const newRun: ClaimVerifyRunItem = {
      run_id: `ws-${Date.now()}`,
      user_id: p.user_id ?? "",
      user_name: p.user_name ?? "Collaborator",
      claim: p.claim ?? "",
      result: p.result,
      created_at: p.created_at ?? new Date().toISOString(),
    };
    setRecentRuns((prev) => [newRun, ...prev]);
  });

  // Restore last result when entering the page (e.g. after switching tabs)
  useEffect(() => {
    const saved = loadPersisted(workspaceId);
    if (saved) {
      setClaim(saved.claim);
      setResult(saved.result);
    } else {
      setClaim("");
      setResult(null);
    }
  }, [workspaceId]);

  async function handleVerify() {
    const trimmed = claim.trim();
    if (!trimmed) {
      setError("Enter a claim to verify.");
      return;
    }
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await verifyClaim(trimmed, null);
      setResult(data);
      savePersisted(workspaceId, trimmed, data);
      // Refresh shared list so this run appears (backend saved it)
      await fetchRecent();
    } catch (e: unknown) {
      const msg = e && typeof e === "object" && "response" in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setError(msg || "Verification failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-4xl">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Claim Verification</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Enter a claim to check against your papers. Results show support, contradiction, and confidence.
        </p>
      </div>

      <div className="rounded-lg border border-border/60 bg-card p-5">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Claim</label>
        <Textarea
          placeholder="e.g. Coffee reduces anxiety in adults."
          value={claim}
          onChange={(e) => setClaim(e.target.value)}
          rows={2}
          className="mt-2 resize-none border-border/60 focus-visible:ring-offset-0"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button onClick={handleVerify} disabled={loading} size="sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Verify
          </Button>
          <span className="text-xs text-muted-foreground">Uses all papers in this workspace.</span>
          <span className="text-xs text-muted-foreground ml-auto">Examples: </span>
          <div className="flex flex-wrap gap-x-2 gap-y-1">
            {EXAMPLE_CLAIMS.map((example) => (
              <button
                key={example}
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground border-b border-transparent hover:border-current"
                onClick={() => setClaim(example)}
              >
                {example.replace(/\.$/, "").slice(0, 28)}{example.length > 28 ? "…" : ""}
              </button>
            ))}
          </div>
        </div>
        {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
      </div>

      {result && <ResultView result={result} />}

      <div className="space-y-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
          <Users className="h-4 w-4" />
          Recent in this workspace
        </p>
        {loadingRecent ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : recentRuns.length === 0 ? (
          <p className="text-sm text-muted-foreground">No verifications yet.</p>
        ) : (
          <div className="space-y-2">
            {recentRuns.map((run) => (
              <RecentRunRow
                key={run.run_id}
                run={run}
                currentUserId={currentUserId}
                expanded={expandedRunId === run.run_id}
                onToggle={() => setExpandedRunId((id) => (id === run.run_id ? null : run.run_id))}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
