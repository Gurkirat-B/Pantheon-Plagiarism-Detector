"use client";

import { useState, useRef, type RefObject } from "react";
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
  Plus,
  Download,
  FolderOpen,
  Loader2,
} from "lucide-react";

import { cn } from "@/lib/utils";
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
import {
  FileUploadDialog,
  type UploadSuccessData,
} from "@/components/FileUploadDialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "@/hooks/use-toast";

import type {
  AssignmentDetail,
  CourseInfo,
  Submission,
  SimilarityReport,
  RepoUpload,
} from "./page";
import {
  mapReport,
  buildLineToBlockMap,
  type ComparisonReport,
  type MatchSeverity,
  type CodeMatch,
} from "@/lib/report_types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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

function getLevelCardClass(level: string): {
  label: string;
  className: string;
} {
  switch (level) {
    case "CRITICAL":
      return {
        label: "CRITICAL",
        className: "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
      };
    case "HIGH":
      return {
        label: "HIGH",
        className:
          "border-orange-200 bg-orange-50 text-orange-700 hover:bg-orange-100",
      };
    case "MEDIUM":
      return {
        label: "MEDIUM",
        className:
          "border-yellow-200 bg-yellow-50 text-yellow-700 hover:bg-yellow-100",
      };
    default:
      return {
        label: "LOW",
        className:
          "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
      };
  }
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

const BLOCK_COLORS = [
  "bg-sky-200",
  "bg-violet-200",
  "bg-emerald-200",
  "bg-amber-200",
  "bg-rose-200",
  "bg-teal-200",
  "bg-orange-200",
  "bg-fuchsia-200",
  "bg-cyan-200",
  "bg-lime-200",
];

function FullCodePanel({
  label,
  fileName,
  code,
  lineToBlockMap,
  language,
  scrollContainerRef,
  onHighlightClick,
}: {
  label: string;
  fileName: string;
  code: string;
  lineToBlockMap: Map<number, number>;
  language: string;
  scrollContainerRef: RefObject<HTMLDivElement>;
  onHighlightClick?: (blockIndex: number) => void;
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
        <p className="mt-1 text-xs text-slate-500">
          Click a highlighted line to scroll the other panel to its match.
        </p>
      </div>

      <div ref={scrollContainerRef} className="flex-1 overflow-auto bg-muted">
        <table className="w-full font-mono text-sm">
          <tbody>
            {lines.map((line, idx) => {
              const lineNum = idx + 1;
              const blockIndex =
                line.trim() === "" ? undefined : lineToBlockMap.get(lineNum);
              const color =
                blockIndex !== undefined
                  ? BLOCK_COLORS[blockIndex % BLOCK_COLORS.length]
                  : undefined;
              const { code: codePart, comment } =
                blockIndex !== undefined
                  ? splitInlineComment(line, language)
                  : { code: line, comment: null };

              return (
                <tr
                  key={lineNum}
                  data-line={lineNum}
                  className={cn(
                    "leading-relaxed",
                    blockIndex !== undefined && "cursor-pointer",
                  )}
                  onClick={
                    blockIndex !== undefined
                      ? () => onHighlightClick?.(blockIndex)
                      : undefined
                  }
                >
                  <td className="w-10 select-none px-3 py-0 text-right align-top text-slate-300">
                    {lineNum}
                  </td>
                  <td className="px-3 py-0">
                    <pre className="whitespace-pre text-slate-800">
                      {color ? (
                        <>
                          <span className={`rounded-sm px-0.5 ${color}`}>
                            {codePart}
                          </span>
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
  emailById,
}: {
  open: boolean;
  onClose: () => void;
  report: ComparisonReport | null;
  emailById: Map<string, string>;
}) {
  const [viewMode, setViewMode] = useState<ViewMode>("blocks");
  const scrollRefA = useRef<HTMLDivElement>(null);
  const scrollRefB = useRef<HTMLDivElement>(null);

  const handleClose = () => {
    setViewMode("blocks");
    onClose();
  };

  if (!report) return null;

  const filesA = Object.keys(report.fileOffsetsA);
  const filesB = Object.keys(report.fileOffsetsB);
  const fileNameA = filesA.length === 1 ? filesA[0] : `${filesA.length} files`;
  const fileNameB = filesB.length === 1 ? filesB[0] : `${filesB.length} files`;

  const lineToBlockMapA = buildLineToBlockMap(report.matches, "A");
  const lineToBlockMapB = buildLineToBlockMap(report.matches, "B");

  const scrollToBlock = (
    highlights: number[],
    containerRef: RefObject<HTMLDivElement>,
  ) => {
    if (highlights.length === 0) return;
    const el = containerRef.current?.querySelector(
      `[data-line="${highlights[0]}"]`,
    );
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-b px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-xl">
                Plagiarism Detection Report
              </DialogTitle>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {emailById.get(report.submissionA) ?? report.submissionA} vs{" "}
                {emailById.get(report.submissionB) ?? report.submissionB} ·{" "}
                {report.language}
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
            <div className="mx-6 mt-5 pb-6">
              <div className="flex h-[80vh] gap-3">
                <FullCodePanel
                  label={emailById.get(report.submissionA) ?? "Submission A"}
                  fileName={fileNameA}
                  code={report.fullCodeA}
                  lineToBlockMap={lineToBlockMapA}
                  language={report.language}
                  scrollContainerRef={scrollRefA}
                  onHighlightClick={(bi) =>
                    scrollToBlock(
                      report.matches[bi]?.lineHighlightsB ?? [],
                      scrollRefB,
                    )
                  }
                />
                <FullCodePanel
                  label={emailById.get(report.submissionB) ?? "Submission B"}
                  fileName={fileNameB}
                  code={report.fullCodeB}
                  lineToBlockMap={lineToBlockMapB}
                  language={report.language}
                  scrollContainerRef={scrollRefB}
                  onHighlightClick={(bi) =>
                    scrollToBlock(
                      report.matches[bi]?.lineHighlightsA ?? [],
                      scrollRefA,
                    )
                  }
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
  repoReports,
  emailById,
  onOpenReport,
}: {
  open: boolean;
  onClose: () => void;
  submission: Submission | null;
  reports: SimilarityReport[];
  repoReports: SimilarityReport[];
  emailById: Map<string, string>;
  onOpenReport: (sr: SimilarityReport) => void;
}) {
  const [manualTab, setManualTab] = useState<"current" | "repo" | null>(null);
  const [prevSubmissionId, setPrevSubmissionId] = useState<string | null>(null);

  // Synchronously reset manual tab when submission changes — avoids post-render flicker
  const currentId = submission?.submission_id ?? null;
  if (currentId !== prevSubmissionId) {
    setPrevSubmissionId(currentId);
    setManualTab(null);
  }

  if (!submission) return null;

  const studentMatching = reports.filter(
    (r) =>
      r.submissionA === submission.submission_id ||
      r.submissionB === submission.submission_id,
  );
  const repoMatching = repoReports.filter(
    (r) =>
      r.submissionA === submission.submission_id ||
      r.submissionB === submission.submission_id,
  );
  const defaultTab: "current" | "repo" =
    studentMatching.length === 0 && repoMatching.length > 0 ? "repo" : "current";
  const tab = manualTab ?? defaultTab;
  const matching = tab === "current" ? studentMatching : repoMatching;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Reports for {submission.email}</DialogTitle>
        </DialogHeader>

        <div className="flex w-fit items-center rounded-lg border bg-muted p-1">
          <button
            onClick={() => setManualTab("current")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "current"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Current Submissions
          </button>
          <button
            onClick={() => setManualTab("repo")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "repo"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            With Repository
          </button>
        </div>

        <div className="mt-2 max-h-[60vh] space-y-3 overflow-y-auto pr-1">
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
              const sev = getLevelCardClass(sr.similarityLevel);
              const reportKey = `${sr.submissionA}_${sr.submissionB}`;

              // For repo tab: the other party is a repo upload — show filename instead of unknown ID
              let otherLabel: string;
              if (tab === "repo" && !emailById.has(otherId)) {
                const repoFiles =
                  otherId === sr.submissionB
                    ? Object.keys(sr.fileOffsetsB)
                    : Object.keys(sr.fileOffsetsA);
                otherLabel =
                  repoFiles.length === 1
                    ? repoFiles[0]
                    : `${repoFiles.length} files`;
              } else {
                otherLabel = emailById.get(otherId) ?? otherId;
              }

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
                        vs {otherLabel}
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

// ─── View Resources Dialog ────────────────────────────────────────────────────

function ViewResourcesDialog({
  open,
  onClose,
  boilerplateFilename,
  repoUploads,
}: {
  open: boolean;
  onClose: () => void;
  boilerplateFilename: string | null;
  repoUploads: RepoUpload[];
}) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-slate-500" />
            Assignment Resources
          </DialogTitle>
        </DialogHeader>
        <div className="mt-2 space-y-3">
          <div className="flex items-center justify-between rounded-lg border bg-slate-50 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-800">
                Boilerplate Code
              </p>
              {boilerplateFilename ? (
                <p className="font-mono text-xs text-slate-600">{boilerplateFilename}</p>
              ) : (
                <p className="text-xs text-muted-foreground">No file uploaded</p>
              )}
            </div>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-sm font-medium text-slate-800 mb-2">Repository Files</p>
            {repoUploads.length === 0 ? (
              <p className="text-xs text-muted-foreground">No files uploaded</p>
            ) : (
              <div className="max-h-[180px] overflow-y-auto space-y-1.5 pr-1">
                {repoUploads.map((upload) => (
                  <div
                    key={upload.upload_id}
                    className="flex items-center justify-between gap-3 rounded-md bg-white border px-3 py-1.5"
                  >
                    <span className="font-mono text-xs text-slate-700 truncate">{upload.filename}</span>
                    <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                      {formatDate(upload.uploaded_at)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Export Confirm Dialog ────────────────────────────────────────────────────

function ExportConfirmDialog({
  open,
  onClose,
  onConfirm,
  loading,
  submissionCount,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading: boolean;
  submissionCount: number;
}) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Export Submissions</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          You are about to export all {submissionCount} student submission
          {submissionCount !== 1 ? "s" : ""} for this assignment. A download
          link will be generated and your download will start automatically.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <LoadingButton
            onClick={onConfirm}
            loading={loading}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            {loading ? "Exporting..." : "Export"}
          </LoadingButton>
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
  title = "Analysis Complete",
  description = "All submission pairs have been compared.",
}: {
  open: boolean;
  onClose: () => void;
  totalPairs: number;
  title?: string;
  description?: string;
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
            <DialogTitle className="text-xl">{title}</DialogTitle>
            <p className="text-sm text-muted-foreground">{description}</p>
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
  initialRepoReports,
  initialBoilerplateFilename,
  initialRepoUploads,
}: {
  assignment: AssignmentDetail;
  course: CourseInfo;
  initialReports: SimilarityReport[];
  initialRepoReports: SimilarityReport[];
  initialBoilerplateFilename: string | null;
  initialRepoUploads: RepoUpload[];
}) {
  const router = useRouter();

  const [reports, setReports] = useState<SimilarityReport[]>(initialReports);
  const [repoReports, setRepoReports] = useState<SimilarityReport[]>(initialRepoReports);
  const [comparingAll, setComparingAll] = useState(false);
  const [comparingRepo, setComparingRepo] = useState(false);
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailSubmission, setDetailSubmission] = useState<Submission | null>(
    null,
  );
  const [successDialogType, setSuccessDialogType] = useState<
    "current" | "repo" | null
  >(null);
  const [compareResult, setCompareResult] = useState<{
    totalPairs: number;
  } | null>(null);
  const [uploadDialogType, setUploadDialogType] = useState<
    "boilerplate" | "repository" | null
  >(null);
  const [exportConfirmOpen, setExportConfirmOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [viewResourcesOpen, setViewResourcesOpen] = useState(false);
  const [boilerplateFilename, setBoilerplateFilename] = useState<string | null>(
    initialBoilerplateFilename,
  );
  const [repoUploads, setRepoUploads] = useState<RepoUpload[]>(initialRepoUploads);

  const submissions = assignment.submissions;

  // Re-fetch reports from the same endpoint used server-side, one call per submission
  const refreshReports = async () => {
    const ids = submissions.map((s) => s.submission_id).join(",");
    const res = await fetch(
      `/api/engine/similarity-report-student?submission_ids=${ids}`,
    );

    if (res.status === 401) {
      router.push("/");
      return;
    }
    if (!res.ok) return;

    const data: SimilarityReport[] = await res.json();
    setReports(Array.isArray(data) ? data : []);
  };

  const refreshRepoReports = async () => {
    const ids = submissions.map((s) => s.submission_id).join(",");
    const res = await fetch(
      `/api/engine/similarity-report-repo?submission_ids=${ids}`,
    );
    if (res.status === 401) {
      router.push("/");
      return;
    }
    if (!res.ok) return;
    const data: SimilarityReport[] = await res.json();
    setRepoReports(Array.isArray(data) ? data : []);
  };

  const handleCompareAll = async () => {
    setComparingAll(true);
    toast({
      title: "Comparison started",
      description:
        "This may take a few seconds. We'll notify you when it's done.",
    });
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
      setCompareResult({ totalPairs: result.total_pairs ?? 0 });
      setSuccessDialogType("current");
    } catch {
      toast({ variant: "destructive", title: "Comparison failed." });
    } finally {
      setComparingAll(false);
    }
  };

  const handleCompareRepo = async () => {
    setComparingRepo(true);
    toast({
      title: "Repository comparison started",
      description:
        "This may take a few seconds. We'll notify you when it's done.",
    });
    try {
      const res = await fetch(
        `/api/engine/assignments/${assignment.assignment_id}/compare-repo`,
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
      await refreshRepoReports();
      setCompareResult({ totalPairs: result.total_pairs ?? 0 });
      setSuccessDialogType("repo");
    } catch {
      toast({ variant: "destructive", title: "Repository comparison failed." });
    } finally {
      setComparingRepo(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await fetch(
        `/api/submissions/${assignment.assignment_id}/export`,
      );
      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();
      const data = await res.json();
      setExportConfirmOpen(false);
      toast({
        title: "Export ready",
        description: `${data.count} submission${data.count !== 1 ? "s" : ""} · ${formatBytes(data.size_bytes)}. Your download will start shortly.`,
      });
      window.open(data.download_url, "_blank");
    } catch {
      toast({ variant: "destructive", title: "Export failed." });
    } finally {
      setExporting(false);
    }
  };

  // The GET endpoint already returns full report data — no second fetch needed
  const handleOpenReport = (sr: SimilarityReport) => {
    const parsed = mapReport(sr);
    setReport(parsed);
    setDetailSubmission(null);
    setDialogOpen(true);
  };

  const emailById = new Map(submissions.map((s) => [s.submission_id, s.email]));

  const submissionsWithReports = new Set([
    ...reports.flatMap((r) => [r.submissionA, r.submissionB]),
    ...repoReports.flatMap((r) => [r.submissionA, r.submissionB]),
  ]);

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

          <div className="flex gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <FolderOpen className="h-4 w-4" />
                  Resources
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>
                    <Plus className="mr-2 h-4 w-4" />
                    Add
                  </DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    <DropdownMenuItem
                      onClick={() => setUploadDialogType("boilerplate")}
                    >
                      Add boilerplate code
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setUploadDialogType("repository")}
                    >
                      Add repository
                    </DropdownMenuItem>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setViewResourcesOpen(true)}>
                  <FolderOpen className="mr-2 h-4 w-4" />
                  View resources
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              variant="outline"
              className="gap-2"
              disabled={submissions.length === 0}
              onClick={() => setExportConfirmOpen(true)}
            >
              <Download className="h-4 w-4" />
              Export
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  disabled={
                    comparingAll || comparingRepo || submissions.length < 2
                  }
                  className="gap-2"
                >
                  {comparingAll || comparingRepo ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  {comparingAll || comparingRepo ? "Analysing..." : "Compare"}
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  disabled={comparingAll || comparingRepo}
                  onClick={handleCompareAll}
                >
                  Current submissions
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={comparingAll || comparingRepo}
                  onClick={handleCompareRepo}
                >
                  With repository
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
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

      <ViewResourcesDialog
        open={viewResourcesOpen}
        onClose={() => setViewResourcesOpen(false)}
        boilerplateFilename={boilerplateFilename}
        repoUploads={repoUploads}
      />

      <ExportConfirmDialog
        open={exportConfirmOpen}
        onClose={() => setExportConfirmOpen(false)}
        onConfirm={handleExport}
        loading={exporting}
        submissionCount={submissions.length}
      />

      <ReportListDialog
        open={detailSubmission !== null}
        onClose={() => setDetailSubmission(null)}
        submission={detailSubmission}
        reports={reports}
        repoReports={repoReports}
        emailById={emailById}
        onOpenReport={handleOpenReport}
      />

      <ComparisonDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        report={report}
        emailById={emailById}
      />

      <CompareAllSuccessDialog
        open={successDialogType !== null}
        onClose={() => setSuccessDialogType(null)}
        totalPairs={compareResult?.totalPairs ?? 0}
        title={
          successDialogType === "repo"
            ? "Repository Analysis Complete"
            : "Analysis Complete"
        }
        description={
          successDialogType === "repo"
            ? "All submission-repository pairs have been analysed."
            : "All submission pairs have been compared."
        }
      />

      <FileUploadDialog
        open={uploadDialogType === "boilerplate"}
        onClose={() => setUploadDialogType(null)}
        title="Add Boilerplate Code"
        description="Upload a zip file containing the boilerplate code for this assignment."
        onUpload={async (file): Promise<UploadSuccessData> => {
          const body = new FormData();
          body.append("file", file);
          const res = await fetch(
            `/api/submissions/boilerplate/${assignment.assignment_id}`,
            { method: "POST", body },
          );
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            throw new Error(data.message ?? "Upload failed. Please try again.");
          }
          setBoilerplateFilename(data.name ?? file.name);
          return {
            details: [
              { label: "File", value: data.name ?? file.name },
              {
                label: "Size",
                value: formatBytes(data.size_bytes ?? file.size),
              },
            ],
          };
        }}
      />

      <FileUploadDialog
        open={uploadDialogType === "repository"}
        onClose={() => setUploadDialogType(null)}
        title="Add Repository"
        description="Upload a zip file containing the reference repository for this assignment."
        onUpload={async (file): Promise<UploadSuccessData> => {
          const body = new FormData();
          body.append("file", file);
          const res = await fetch(
            `/api/submissions/repo/${assignment.assignment_id}`,
            { method: "POST", body },
          );
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            throw new Error(data.message ?? "Upload failed. Please try again.");
          }
          setRepoUploads((prev) => [
            ...prev,
            {
              upload_id: crypto.randomUUID(),
              filename: file.name,
              uploaded_at: new Date().toISOString(),
            },
          ]);
          return {
            details: [
              {
                label: "Files uploaded",
                value: String(data.uploaded_count ?? 0),
              },
            ],
          };
        }}
      />
    </main>
  );
}
