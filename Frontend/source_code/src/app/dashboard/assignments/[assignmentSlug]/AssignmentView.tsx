"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  TrendingUp,
  AlertTriangle,
  Users,
  Code2,
  Minus,
  Clock,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import type { AssignmentDetail, CourseInfo, Submission } from "./page";
import {
  parseReport,
  type ComparisonReport,
  type MatchSeverity,
} from "@/lib/parse_report";
import { LoadingButton } from "@/components/LoadingButton";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr: string) {
  const [year, month, day] = dateStr.split("T")[0].split("-");
  return `${parseInt(month)}/${parseInt(day)}/${year}`;
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "numeric",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function getSeverityClass(severity: MatchSeverity) {
  switch (severity) {
    case "HIGH":
      return "border-red-200 bg-red-50 text-red-700";
    case "MEDIUM":
      return "border-orange-200 bg-orange-50 text-orange-700";
    case "LOW":
      return "border-yellow-200 bg-yellow-50 text-yellow-700";
  }
}

function getLevelColor(level: string) {
  switch (level) {
    case "CRITICAL":
      return "text-red-600";
    case "HIGH":
      return "text-orange-500";
    case "MEDIUM":
      return "text-yellow-600";
    default:
      return "text-emerald-600";
  }
}

function getLevelBg(level: string) {
  switch (level) {
    case "CRITICAL":
      return "bg-red-50 border-red-200";
    case "HIGH":
      return "bg-orange-50 border-orange-200";
    case "MEDIUM":
      return "bg-yellow-50 border-yellow-200";
    default:
      return "bg-emerald-50 border-emerald-200";
  }
}

// ─── Code Panel ───────────────────────────────────────────────────────────────

function CodePanel({
  label,
  fileName,
  lines,
  code,
}: {
  label: string;
  fileName: string;
  lines: string;
  code: string;
}) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-slate-700">
      <div className="border-b border-slate-700 bg-slate-800 px-4 py-3">
        <p className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-300">
          {label}
        </p>
        <p className="mt-0.5 font-mono text-sm font-semibold text-slate-100">
          {fileName}
        </p>
        <p className="font-mono text-xs text-slate-400">Lines {lines}</p>
      </div>
      <div className="flex-1 overflow-auto bg-slate-900 p-4">
        <pre className="whitespace-pre font-mono text-sm leading-relaxed text-emerald-400">
          {code || "(no code snippet available)"}
        </pre>
      </div>
    </div>
  );
}

// ─── Match Block ──────────────────────────────────────────────────────────────

function MatchBlock({ match }: { match: ComparisonReport["matches"][number] }) {
  const [expanded, setExpanded] = useState(match.severity === "HIGH");

  return (
    <div className={`rounded-lg border ${getSeverityClass(match.severity)}`}>
      {/* Block header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <Badge
            variant="outline"
            className={`text-xs font-semibold ${getSeverityClass(match.severity)}`}
          >
            {match.severity}
          </Badge>
          <span className="text-sm font-medium">
            Block {match.index} — {match.fileA} vs {match.fileB}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            A: lines {match.linesA} · B: lines {match.linesB}
          </span>
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </div>
      </button>

      {/* Expandable code panels */}
      {expanded && (
        <div
          className="border-current/10 flex gap-3 border-t p-4"
          style={{ minHeight: "200px" }}
        >
          <CodePanel
            label="Submission A"
            fileName={match.fileA}
            lines={match.linesA}
            code={match.codeA}
          />
          <CodePanel
            label="Submission B"
            fileName={match.fileB}
            lines={match.linesB}
            code={match.codeB}
          />
        </div>
      )}
    </div>
  );
}

// ─── Comparison Dialog ────────────────────────────────────────────────────────

function ComparisonDialog({
  open,
  onClose,
  report,
}: {
  open: boolean;
  onClose: () => void;
  report: ComparisonReport | null;
}) {
  if (!report) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle className="text-xl">
            Plagiarism Detection Report
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            {report.submissionA} vs {report.submissionB} · {report.language}
          </p>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {/* ── Summary banner ── */}
          <div
            className={`mx-6 mt-6 rounded-xl border p-5 ${getLevelBg(report.plagiarismLevel)}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldAlert
                  className={`h-6 w-6 ${getLevelColor(report.plagiarismLevel)}`}
                />
                <div>
                  <p
                    className={`text-2xl font-bold ${getLevelColor(report.plagiarismLevel)}`}
                  >
                    {report.similarityScore}% Similarity
                  </p>
                  <p
                    className={`text-sm font-medium ${getLevelColor(report.plagiarismLevel)}`}
                  >
                    {report.plagiarismLevel} ({report.levelThreshold})
                  </p>
                </div>
              </div>

              {/* Block breakdown */}
              <div className="flex items-center gap-3 text-sm">
                <span className="rounded-md bg-red-100 px-2.5 py-1 font-semibold text-red-700">
                  {report.highCount} HIGH
                </span>
                <span className="rounded-md bg-orange-100 px-2.5 py-1 font-semibold text-orange-700">
                  {report.mediumCount} MEDIUM
                </span>
                <span className="rounded-md bg-yellow-100 px-2.5 py-1 font-semibold text-yellow-700">
                  {report.lowCount} LOW
                </span>
              </div>
            </div>
          </div>

          {/* ── Techniques ── */}
          {report.techniques.length > 0 && (
            <div className="mx-6 mt-5">
              <p className="mb-2 text-sm font-semibold text-slate-700">
                Alteration Techniques Detected
              </p>
              <div className="flex flex-wrap gap-2">
                {report.techniques.map((t) => (
                  <Badge key={t} variant="outline" className="text-xs">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* ── Matching blocks ── */}
          <div className="mx-6 my-5 space-y-3">
            <p className="text-sm font-semibold text-slate-700">
              Matching Code Sections ({report.totalBlocks} blocks)
            </p>
            {report.matches.map((match) => (
              <MatchBlock key={match.index} match={match} />
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Submission Row ───────────────────────────────────────────────────────────

function SubmissionRow({
  submission,
  isSelected,
  onSelect,
  onDetail,
  comparisonScore,
}: {
  submission: Submission;
  isSelected: boolean;
  onSelect: () => void;
  onDetail: () => void;
  comparisonScore?: number | null;
}) {
  const [hovered, setHovered] = useState(false);
  const showCheckbox = hovered || isSelected;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`flex items-center justify-between rounded-lg border px-5 py-4 transition-colors ${
        isSelected
          ? "border-slate-800 bg-slate-50 ring-1 ring-slate-800"
          : "bg-white hover:bg-slate-50"
      }`}
    >
      {/* Left */}
      <div className="flex items-center gap-4">
        <div
          className={`transition-opacity ${showCheckbox ? "opacity-100" : "opacity-0"}`}
        >
          <Checkbox
            checked={isSelected}
            onCheckedChange={onSelect}
            aria-label="Select submission"
          />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-slate-800">
              {submission.email}
            </span>
            <Badge variant="outline" className="font-mono text-xs">
              {submission.original_zip_name}
            </Badge>
            <Badge
              variant="outline"
              className={`text-xs capitalize ${
                submission.status === "accepted"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 text-slate-500"
              }`}
            >
              {submission.status}
            </Badge>
          </div>
          <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            Submitted: {formatDateTime(submission.submitted_at)}
          </p>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">
        {comparisonScore != null && (
          <span
            className={`text-lg font-bold tabular-nums ${
              comparisonScore >= 60
                ? "text-red-500"
                : comparisonScore >= 30
                  ? "text-orange-400"
                  : "text-emerald-500"
            }`}
          >
            {comparisonScore}%
          </span>
        )}
        <Button
          size="sm"
          variant="outline"
          onClick={onDetail}
          className="gap-1.5"
        >
          <Code2 className="h-3.5 w-3.5" />
          Detail
        </Button>
      </div>
    </div>
  );
}

// ─── Main Client Component ────────────────────────────────────────────────────

export function AssignmentView({
  assignment,
  course,
}: {
  assignment: AssignmentDetail;
  course: CourseInfo;
}) {
  const router = useRouter();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [comparing, setComparing] = useState(false);

  // Comparison result lives in state — no persistence yet
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Track which submission pair was last compared so we can show their score
  const [comparedPair, setComparedPair] = useState<{
    idA: string;
    idB: string;
    score: number;
  } | null>(null);

  const submissions = assignment.submissions;

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= 2) return prev;
        next.add(id);
      }
      return next;
    });
  };

  const handleCompare = async () => {
    const [idA, idB] = Array.from(selectedIds);
    if (!idA || !idB) return;

    setComparing(true);
    try {
      const res = await fetch(
        `/api/engine/assignments/${assignment.assignment_id}/compare`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            submission_a_id: idA,
            submission_b_id: idB,
          }),
        },
      );

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      const text = await res.text();
      const parsed = parseReport(text);
      setReport(parsed);
      setComparedPair({ idA, idB, score: parsed.similarityScore });
      setDialogOpen(true);
    } catch {
      console.error("Comparison failed.");
    } finally {
      setComparing(false);
    }
  };

  // Opens the dialog for the last comparison result
  const handleDetail = (submission: Submission) => {
    // Only open if this submission was part of the last comparison
    const isPartOfComparison =
      comparedPair &&
      (comparedPair.idA === submission.submission_id ||
        comparedPair.idB === submission.submission_id);

    if (isPartOfComparison && report) {
      setDialogOpen(true);
    }
    // If no comparison yet, detail does nothing (button is still visible but inert)
    // This will be extended when comparison storage is added
  };

  const selectedCount = selectedIds.size;
  const canTriggerCompare = selectedCount === 2;

  // ── Stats ──────────────────────────────────────────────────────────────────
  const avgScore = report ? report.similarityScore : null;
  const highRisk = report && report.plagiarismLevel === "CRITICAL" ? 1 : 0;

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-10 min-[2000px]:max-w-[2000px]">
      {/* Back */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.back()}
        className="-ml-2 mb-6 gap-1.5 text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Button>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="font-medium">{course.code}</span>
          <Minus className="h-3 w-3" />
          <span>{course.name}</span>
        </div>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
          {assignment.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          Due {formatDate(assignment.due_date)} ·{" "}
          <span className="capitalize">{assignment.language}</span>
        </p>
      </div>

      {/* Stat cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
              <Users className="h-5 w-5 text-slate-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">
                {submissions.length}
              </p>
              <p className="text-sm text-muted-foreground">Total Submissions</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-50">
              <TrendingUp className="h-5 w-5 text-orange-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">
                {avgScore != null ? `${avgScore}%` : "—"}
              </p>
              <p className="text-sm text-muted-foreground">Avg. Similarity</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <AlertTriangle className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{highRisk}</p>
              <p className="text-sm text-muted-foreground">
                High Risk (&ge;60%)
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Submissions list */}
      <div className="rounded-xl border bg-white shadow-sm">
        <div className="flex items-center justify-between px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Submissions —{" "}
              <span className="text-slate-500">{assignment.title}</span>
            </h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {submissions.length} submission
              {submissions.length !== 1 ? "s" : ""} · Select exactly 2 to
              compare
            </p>
          </div>

          <LoadingButton
            onClick={handleCompare}
            disabled={!canTriggerCompare}
            loading={comparing}
            className="gap-2"
          >
            <Code2 className="h-4 w-4" />
            {comparing ? "Analysing..." : "Compare Selected"}
            {!comparing && selectedCount > 0 && (
              <span className="ml-1 rounded-full bg-white/20 px-1.5 py-0.5 text-xs">
                {selectedCount}/2
              </span>
            )}
          </LoadingButton>
        </div>

        <Separator />

        <div className="space-y-3 p-6">
          {submissions.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No submissions yet for this assignment.
            </div>
          ) : (
            submissions.map((submission) => {
              const isPartOfComparison =
                comparedPair &&
                (comparedPair.idA === submission.submission_id ||
                  comparedPair.idB === submission.submission_id);

              return (
                <SubmissionRow
                  key={submission.submission_id}
                  submission={submission}
                  isSelected={selectedIds.has(submission.submission_id)}
                  onSelect={() => toggleSelect(submission.submission_id)}
                  onDetail={() => handleDetail(submission)}
                  comparisonScore={
                    isPartOfComparison ? comparedPair!.score : null
                  }
                />
              );
            })
          )}
        </div>
      </div>

      {/* Comparison dialog */}
      <ComparisonDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        report={report}
      />
    </main>
  );
}
