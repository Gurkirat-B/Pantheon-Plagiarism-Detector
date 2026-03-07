"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Users,
  CheckCircle2,
  Code2,
  AlertTriangle,
  Minus,
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  getSubmissionById,
  type Submission,
  type Assignment,
  type Course,
} from "@/app/dashboard/data";

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

function getSimilarityColor(score: number): string {
  if (score >= 60) return "text-red-500";
  if (score >= 30) return "text-orange-400";
  return "text-emerald-500";
}

function getSimilarityBadgeClass(score: number): string {
  if (score >= 60) return "bg-red-500 text-white hover:bg-red-500";
  if (score >= 30) return "bg-orange-400 text-white hover:bg-orange-400";
  return "bg-emerald-500 text-white hover:bg-emerald-500";
}

function SimilarityIcon({ score }: { score: number }) {
  if (score >= 60) return <TrendingUp className="h-4 w-4 text-red-500" />;
  if (score >= 30) return <TrendingDown className="h-4 w-4 text-orange-400" />;
  return <TrendingDown className="h-4 w-4 text-emerald-500" />;
}

// ─── Code Block ───────────────────────────────────────────────────────────────

function CodeBlock({
  studentId,
  fileName,
  code,
}: {
  studentId: string;
  fileName: string;
  code: string;
}) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-slate-700">
      {/* header */}
      <div className="border-b border-slate-700 bg-slate-800 px-4 py-3">
        <p className="font-mono text-sm font-semibold text-slate-100">
          Student: {studentId}
        </p>
        <p className="font-mono text-xs text-slate-400">{fileName}</p>
      </div>
      {/* code */}
      <div className="flex-1 overflow-auto bg-slate-900 p-4">
        <pre className="whitespace-pre font-mono text-sm leading-relaxed text-emerald-400">
          {code}
        </pre>
      </div>
    </div>
  );
}

// ─── Compare Dialog ───────────────────────────────────────────────────────────

function CompareDialog({
  open,
  onClose,
  submission,
  comparable,
}: {
  open: boolean;
  onClose: () => void;
  submission: Submission | null;
  comparable: Submission | null;
}) {
  if (!submission || !comparable) return null;

  const score = submission.similarityScore;
  const isHigh = score >= 60;
  const isMed = score >= 30 && score < 60;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-5xl flex-col gap-0 overflow-hidden p-0">
        {/* Header */}
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle className="text-xl">
            Side-by-Side Code Comparison
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            Similarity Score:{" "}
            <span className={`font-semibold ${getSimilarityColor(score)}`}>
              {score}%
            </span>{" "}
            |{" "}
            {isHigh
              ? "High structural similarity detected in loop implementation and variable usage patterns"
              : isMed
                ? "Moderate similarity detected in overall structure"
                : "Low similarity — submissions appear independently written"}
          </p>
        </DialogHeader>

        {/* Code panels */}
        <div className="flex flex-1 gap-4 overflow-hidden p-6">
          <CodeBlock
            studentId={submission.studentId}
            fileName={submission.fileName}
            code={submission.code}
          />
          <CodeBlock
            studentId={comparable.studentId}
            fileName={comparable.fileName}
            code={comparable.code}
          />
        </div>

        {/* Alert */}
        <div className="px-6 pb-6">
          {isHigh ? (
            <Alert className="border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <AlertTitle className="text-red-700">
                High Similarity Detected
              </AlertTitle>
              <AlertDescription className="text-red-600">
                Lines 5–9 show structural similarity. Variable names differ but
                logic is nearly identical.
              </AlertDescription>
            </Alert>
          ) : isMed ? (
            <Alert className="border-orange-200 bg-orange-50">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              <AlertTitle className="text-orange-700">
                Moderate Similarity Detected
              </AlertTitle>
              <AlertDescription className="text-orange-600">
                Some shared patterns found, but overall structure differs.
                Manual review recommended.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert className="border-emerald-200 bg-emerald-50">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <AlertTitle className="text-emerald-700">
                Low Similarity
              </AlertTitle>
              <AlertDescription className="text-emerald-600">
                Submissions appear independently written. No significant
                structural overlap detected.
              </AlertDescription>
            </Alert>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Submission Row ───────────────────────────────────────────────────────────

function SubmissionRow({
  submission,
  onCompare,
}: {
  submission: Submission;
  onCompare: () => void;
}) {
  const score = submission.similarityScore;

  return (
    <div className="flex items-center justify-between rounded-lg border bg-white px-5 py-4 transition-colors hover:bg-slate-50">
      {/* Left */}
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-slate-800">
            Student: {submission.studentId}
          </span>
          <Badge variant="outline" className="font-mono text-xs">
            {submission.fileName}
          </Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Submitted: {formatDateTime(submission.submittedAt)}
        </p>
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">
        {/* Score */}
        <div className="flex items-center gap-1.5">
          <SimilarityIcon score={score} />
          <span
            className={`text-2xl font-bold tabular-nums ${getSimilarityColor(score)}`}
          >
            {score}%
          </span>
        </div>

        {/* Similarity badge */}
        <Badge className={`text-xs ${getSimilarityBadgeClass(score)}`}>
          Similarity
        </Badge>

        {/* Compare button */}
        <Button size="sm" onClick={onCompare} className="gap-1.5">
          <Code2 className="h-3.5 w-3.5" />
          Compare
        </Button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function AssignmentView({
  assignment,
  course,
  submissions,
}: {
  assignment: Assignment;
  course: Course;
  submissions: Submission[];
}) {
  const router = useRouter();
  const [compareOpen, setCompareOpen] = useState(false);
  const [selectedSubmission, setSelectedSubmission] =
    useState<Submission | null>(null);
  const [comparableSubmission, setComparableSubmission] =
    useState<Submission | null>(null);

  const handleCompare = (submission: Submission) => {
    const comparable = getSubmissionById(submission.mostSimilarSubmissionId);
    setSelectedSubmission(submission);
    setComparableSubmission(comparable ?? null);
    setCompareOpen(true);
  };

  // ── Stats ──────────────────────────────────────────────────────────────────
  const avgScore =
    submissions.length > 0
      ? Math.round(
          submissions.reduce((acc, s) => acc + s.similarityScore, 0) /
            submissions.length,
        )
      : 0;
  const highRisk = submissions.filter((s) => s.similarityScore >= 60).length;

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
          <span>{course.code}</span>
          <Minus className="h-3 w-3" />
          <span>{course.name}</span>
        </div>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
          {assignment.code}: {assignment.title}
        </h1>
        <p className="mt-1 text-muted-foreground">
          Due{" "}
          {(() => {
            const [year, month, day] = assignment.dueDate.split("-");
            return `${parseInt(month)}/${parseInt(day)}/${year}`;
          })()}
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
              <p className="text-2xl font-bold text-slate-800">{avgScore}%</p>
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
        <div className="px-6 py-5">
          <h2 className="text-lg font-semibold text-slate-800">
            Submissions —{" "}
            <span className="text-slate-500">{assignment.title}</span>
          </h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Showing {submissions.length} of {submissions.length} submissions
          </p>
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
                key={submission.id}
                submission={submission}
                onCompare={() => handleCompare(submission)}
              />
            ))
          )}
        </div>
      </div>

      {/* Compare Dialog */}
      <CompareDialog
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        submission={selectedSubmission}
        comparable={comparableSubmission}
      />
    </main>
  );
}
