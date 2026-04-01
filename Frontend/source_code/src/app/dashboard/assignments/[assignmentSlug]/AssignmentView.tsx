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
  Layers,
  FileCode,
  Play,
  Info,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { LoadingButton } from "@/components/LoadingButton";
import { toast } from "@/hooks/use-toast";

import type {
  AssignmentDetail,
  CourseInfo,
  Submission,
  SimilarityReport,
} from "./page";
import {
  mapReport,
  buildHighlightMap,
  type ComparisonReport,
  type MatchSeverity,
  type CodeMatch,
} from "@/lib/report_types";

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

function getHighlightBg(severity: MatchSeverity) {
  switch (severity) {
    case "HIGH":
      return "bg-red-300";
    case "MEDIUM":
      return "bg-orange-200";
    case "LOW":
      return "bg-yellow-200";
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

// Score is 0–100 (from similarityScore field)
function getScoreSeverity(score: number): {
  label: string;
  className: string;
} {
  if (score >= 80)
    return {
      label: "HIGH",
      className: "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
    };
  if (score >= 50)
    return {
      label: "MEDIUM",
      className:
        "border-yellow-200 bg-yellow-50 text-yellow-700 hover:bg-yellow-100",
    };
  return {
    label: "LOW",
    className:
      "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
  };
}

// ─── Inline comment splitter ──────────────────────────────────────────────────

function splitInlineComment(
  line: string,
  language: string,
): { code: string; comment: string | null } {
  const lang = language.toLowerCase();

  const markers: string[] = [];
  if (["java", "c", "cpp", "js", "ts"].some((l) => lang.includes(l))) {
    markers.push("//");
  }
  if (lang.includes("python")) {
    markers.push("#");
  }
  const blockIdx = line.indexOf("/*");
  if (blockIdx !== -1 && line.indexOf("*/", blockIdx) !== -1) {
    return {
      code: line.slice(0, blockIdx),
      comment: line.slice(blockIdx),
    };
  }

  let earliest: { idx: number; marker: string } | null = null;
  for (const marker of markers) {
    const idx = findCommentIndex(line, marker);
    if (idx !== -1 && (earliest === null || idx < earliest.idx)) {
      earliest = { idx, marker };
    }
  }

  if (!earliest) return { code: line, comment: null };
  return {
    code: line.slice(0, earliest.idx),
    comment: line.slice(earliest.idx),
  };
}

function findCommentIndex(line: string, marker: string): number {
  let inSingle = false;
  let inDouble = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle;
      continue;
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble;
      continue;
    }
    if (!inSingle && !inDouble && line.startsWith(marker, i)) return i;
  }
  return -1;
}

// ─── Match Code Panel ─────────────────────────────────────────────────────────

function MatchCodePanel({
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

// ─── Full Code Panel ──────────────────────────────────────────────────────────

function FullCodePanel({
  label,
  fileName,
  code,
  highlightMap,
  language,
}: {
  label: string;
  fileName: string;
  code: string;
  highlightMap: Map<number, MatchSeverity>;
  language: string;
}) {
  const lines = code.split("\n");

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-slate-200">
      <div className="border-b border-slate-200 bg-gray-200 px-4 py-3">
        <p className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
          {label}
        </p>
        <p className="mt-0.5 font-mono text-sm font-semibold text-slate-800">
          {fileName}
        </p>
        <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-3 rounded-sm bg-red-300" />
            High
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-3 rounded-sm bg-orange-200" />
            Medium
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-3 rounded-sm bg-yellow-200" />
            Low
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-muted">
        <table className="w-full font-mono text-sm">
          <tbody>
            {lines.map((line, idx) => {
              const lineNum = idx + 1;
              const severity = highlightMap.get(lineNum);
              const { code: codePart, comment } = severity
                ? splitInlineComment(line, language)
                : { code: line, comment: null };

              const highlightSpanClass = severity
                ? `rounded-sm px-0.5 ${getHighlightBg(severity)}`
                : "";

              return (
                <tr key={lineNum} className="leading-relaxed">
                  <td className="w-10 select-none px-3 py-0 text-right align-top text-slate-300">
                    {lineNum}
                  </td>
                  <td className="px-3 py-0">
                    <pre className="whitespace-pre text-slate-800">
                      {severity ? (
                        <>
                          <span className={highlightSpanClass}>{codePart}</span>
                          {comment && <span>{comment}</span>}
                        </>
                      ) : (
                        line
                      )}
                    </pre>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Match Block ──────────────────────────────────────────────────────────────

function MatchBlock({ match }: { match: CodeMatch }) {
  const [expanded, setExpanded] = useState(match.severity === "HIGH");

  return (
    <div className={`rounded-lg border ${getSeverityClass(match.severity)}`}>
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

      {expanded && (
        <div
          className="border-current/10 flex gap-3 border-t p-4"
          style={{ minHeight: "200px" }}
        >
          <MatchCodePanel
            label="Submission A"
            fileName={match.fileA}
            lines={match.linesA}
            code={match.codeA}
          />
          <MatchCodePanel
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

type ViewMode = "blocks" | "fullcode";

function ComparisonDialog({
  open,
  onClose,
  report,
}: {
  open: boolean;
  onClose: () => void;
  report: ComparisonReport | null;
}) {
  const [viewMode, setViewMode] = useState<ViewMode>("blocks");

  if (!report) return null;

  const fileNameA = Object.keys(report.fullCodeA)[0] ?? "Submission A";
  const fileNameB = Object.keys(report.fullCodeB)[0] ?? "Submission B";
  const fullCodeA = report.fullCodeA[fileNameA] ?? "";
  const fullCodeB = report.fullCodeB[fileNameB] ?? "";

  const highlightMapA = buildHighlightMap(report.matches, fileNameA, "A");
  const highlightMapB = buildHighlightMap(report.matches, fileNameB, "B");

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-b px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-xl">
                Plagiarism Detection Report
              </DialogTitle>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {report.submissionA} vs {report.submissionB} · {report.language}
              </p>
            </div>

            <div className="flex items-center rounded-lg border bg-muted p-1">
              <button
                onClick={() => setViewMode("blocks")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === "blocks"
                    ? "bg-white text-slate-800 shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Layers className="h-3.5 w-3.5" />
                Match Blocks
              </button>
              <button
                onClick={() => setViewMode("fullcode")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === "fullcode"
                    ? "bg-white text-slate-800 shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <FileCode className="h-3.5 w-3.5" />
                Full Code
              </button>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
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
                    {report.plagiarismLevel}
                  </p>
                </div>
              </div>

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

          {viewMode === "blocks" && (
            <div className="mx-6 my-5 space-y-3">
              <p className="text-sm font-semibold text-slate-700">
                Matching Code Sections ({report.totalBlocks} blocks)
              </p>
              {report.matches.map((match) => (
                <MatchBlock key={match.index} match={match} />
              ))}
            </div>
          )}

          {viewMode === "fullcode" && (
            <div className="mx-6 my-5">
              <p className="mb-3 text-sm font-semibold text-slate-700">
                Full Submissions — highlighted lines indicate matching sections
              </p>
              <div className="flex gap-3" style={{ minHeight: "500px" }}>
                <FullCodePanel
                  label="Submission A"
                  fileName={fileNameA}
                  code={fullCodeA}
                  highlightMap={highlightMapA}
                  language={report.language}
                />
                <FullCodePanel
                  label="Submission B"
                  fileName={fileNameB}
                  code={fullCodeB}
                  highlightMap={highlightMapB}
                  language={report.language}
                />
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Report List Dialog ───────────────────────────────────────────────────────

function ReportListDialog({
  open,
  onClose,
  submission,
  reports,
  onOpenReport,
}: {
  open: boolean;
  onClose: () => void;
  submission: Submission | null;
  reports: SimilarityReport[];
  onOpenReport: (sr: SimilarityReport) => void;
}) {
  if (!submission) return null;

  // Match using the camelCase fields the API actually returns
  const matching = reports.filter(
    (r) =>
      r.submissionA === submission.submission_id ||
      r.submissionB === submission.submission_id,
  );

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Reports for {submission.email}</DialogTitle>
        </DialogHeader>
        <div className="mt-2 space-y-3">
          {matching.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No reports found.
            </p>
          ) : (
            matching.map((sr) => {
              const otherId =
                sr.submissionA === submission.submission_id
                  ? sr.submissionB
                  : sr.submissionA;
              // similarityScore is already 0–100
              const sev = getScoreSeverity(sr.similarityScore);
              const reportKey = `${sr.submissionA}_${sr.submissionB}`;

              return (
                <button
                  key={reportKey}
                  onClick={() => onOpenReport(sr)}
                  className={`w-full rounded-lg border p-4 text-left transition-colors ${sev.className}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold tabular-nums">
                          {sr.similarityScore.toFixed(1)}%
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-xs font-semibold ${sev.className}`}
                        >
                          {sev.label}
                        </Badge>
                      </div>
                      <p className="font-mono text-xs text-muted-foreground">
                        vs {otherId}
                      </p>
                      <p className="text-xs capitalize text-muted-foreground">
                        {sr.language}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Compare All Success Dialog ───────────────────────────────────────────────

function CompareAllSuccessDialog({
  open,
  onClose,
  totalPairs,
  flaggedPairs,
}: {
  open: boolean;
  onClose: () => void;
  totalPairs: number;
  flaggedPairs: number;
}) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm text-center">
        <div className="flex flex-col items-center gap-4 py-4">
          {/* Icon */}
          <div className="flex h-14 w-14 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50">
            <ShieldAlert className="h-7 w-7 text-emerald-600" />
          </div>

          <div className="space-y-1">
            <DialogTitle className="text-xl">Analysis Complete</DialogTitle>
            <p className="text-sm text-muted-foreground">
              All submission pairs have been compared.
            </p>
          </div>

          {/* Stats */}
          <div className="w-full divide-y rounded-lg border bg-slate-50">
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-sm text-muted-foreground">
                Total pairs analysed
              </span>
              <span className="text-sm font-semibold text-slate-800">
                {totalPairs}
              </span>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-sm text-muted-foreground">
                Flagged pairs
              </span>
              <span
                className={`text-sm font-semibold ${flaggedPairs > 0 ? "text-red-600" : "text-emerald-600"}`}
              >
                {flaggedPairs}
              </span>
            </div>
          </div>
          <div className="flex w-full items-start gap-2.5 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-left">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
            <p className="text-xs leading-relaxed text-blue-700">
              To review results, click the{" "}
              <span className="inline-flex items-center gap-1 font-medium">
                <Code2 className="h-3 w-3" />
                Detail
              </span>{" "}
              button on any submission to see its similarity reports.
            </p>
          </div>
          <Button onClick={onClose} className="w-full">
            Done
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Submission Row ───────────────────────────────────────────────────────────

function SubmissionRow({
  submission,
  hasReports,
  isHighRisk,
  onDetail,
}: {
  submission: Submission;
  hasReports: boolean;
  isHighRisk: boolean;
  onDetail: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border bg-white px-5 py-4 transition-colors hover:bg-slate-50">
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-slate-800">
            {submission.email}
          </span>
          <Badge variant="outline" className="font-mono text-xs">
            {submission.original_zip_name}
          </Badge>
          {hasReports ? (
            <Badge
              variant="outline"
              className="border-blue-200 bg-blue-50 text-xs text-blue-700"
            >
              Compared
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="border-slate-200 bg-slate-50 text-xs text-slate-400"
            >
              Not compared
            </Badge>
          )}
          {isHighRisk && (
            <Badge
              variant="outline"
              className="border-red-200 bg-red-50 text-xs text-red-700"
            >
              High Risk
            </Badge>
          )}
        </div>
        <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          Submitted: {formatDateTime(submission.submitted_at)}
        </p>
      </div>

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
  );
}

// ─── Main Client Component ────────────────────────────────────────────────────

export function AssignmentView({
  assignment,
  course,
  initialReports,
}: {
  assignment: AssignmentDetail;
  course: CourseInfo;
  initialReports: SimilarityReport[];
}) {
  const router = useRouter();

  const [reports, setReports] = useState<SimilarityReport[]>(initialReports);
  const [comparingAll, setComparingAll] = useState(false);
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailSubmission, setDetailSubmission] = useState<Submission | null>(
    null,
  );
  const [successDialogOpen, setSuccessDialogOpen] = useState(false);
  const [compareAllResult, setCompareAllResult] = useState<{
    totalPairs: number;
    flaggedPairs: number;
  } | null>(null);

  const submissions = assignment.submissions;

  // Re-fetch reports from the same endpoint used server-side, one call per submission
  const refreshReports = async () => {
    const ids = submissions.map((s) => s.submission_id).join(",");
    const res = await fetch(
      `/api/engine/similarity-report?submission_ids=${ids}`,
    );

    if (res.status === 401) {
      router.push("/");
      return;
    }
    if (!res.ok) return;

    const data: SimilarityReport[] = await res.json();
    setReports(Array.isArray(data) ? data : []);
  };

  const handleCompareAll = async () => {
    setComparingAll(true);
    try {
      const res = await fetch(
        `/api/engine/assignments/${assignment.assignment_id}/compare-all`,
        { method: "POST", headers: { Accept: "application/json" } },
      );

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (res.status === 400) {
        toast({ variant: "destructive", title: "Invalid assignment ID" });
        return;
      }
      if (!res.ok) throw new Error();

      const result = await res.json();
      await refreshReports();
      setCompareAllResult({
        totalPairs: result.total_pairs ?? 0,
        flaggedPairs: result.flagged_pairs ?? 0,
      });
      setSuccessDialogOpen(true);
    } catch {
      toast({ variant: "destructive", title: "Comparison failed." });
    } finally {
      setComparingAll(false);
    }
  };

  // The GET endpoint already returns full report data — no second fetch needed
  const handleOpenReport = (sr: SimilarityReport) => {
    const parsed = mapReport(sr);
    setReport(parsed);
    setDetailSubmission(null);
    setDialogOpen(true);
  };

  const submissionsWithReports = new Set(
    reports.flatMap((r) => [r.submissionA, r.submissionB]),
  );

  const submissionsHighRisk = new Set(
    reports
      .filter((r) => r.similarityScore >= 80)
      .flatMap((r) => [r.submissionA, r.submissionB]),
  );

  // Stats: similarityScore is already 0–100
  const avgScore =
    reports.length > 0
      ? Math.round(
          (reports.reduce((sum, r) => sum + r.similarityScore, 0) /
            reports.length) *
            10,
        ) / 10
      : null;
  const highRisk = reports.filter((r) => r.similarityScore >= 80).length;

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-10 min-[2000px]:max-w-[2000px]">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          router.push("/dashboard");
          router.refresh();
        }}
        className="-ml-2 mb-6 gap-1.5 text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Button>

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
                High Risk (&ge;80%)
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="rounded-xl border bg-white shadow-sm">
        <div className="flex items-center justify-between px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Submissions —{" "}
              <span className="text-slate-500">{assignment.title}</span>
            </h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {submissions.length} submission
              {submissions.length !== 1 ? "s" : ""}
            </p>
          </div>

          <LoadingButton
            onClick={handleCompareAll}
            loading={comparingAll}
            disabled={submissions.length < 2}
            className="gap-2"
          >
            <Play className="h-4 w-4" />
            {comparingAll ? "Analysing..." : "Compare All"}
          </LoadingButton>
        </div>

        <Separator />

        <div className="space-y-3 p-6">
          {submissions.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No submissions yet for this assignment.
            </div>
          ) : (
            submissions.map((submission) => (
              <SubmissionRow
                key={submission.submission_id}
                submission={submission}
                hasReports={submissionsWithReports.has(
                  submission.submission_id,
                )}
                isHighRisk={submissionsHighRisk.has(submission.submission_id)}
                onDetail={() => setDetailSubmission(submission)}
              />
            ))
          )}
        </div>
      </div>

      <ReportListDialog
        open={detailSubmission !== null}
        onClose={() => setDetailSubmission(null)}
        submission={detailSubmission}
        reports={reports}
        onOpenReport={handleOpenReport}
      />

      <ComparisonDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        report={report}
      />

      <CompareAllSuccessDialog
        open={successDialogOpen}
        onClose={() => setSuccessDialogOpen(false)}
        totalPairs={compareAllResult?.totalPairs ?? 0}
        flaggedPairs={compareAllResult?.flaggedPairs ?? 0}
      />
    </main>
  );
}
