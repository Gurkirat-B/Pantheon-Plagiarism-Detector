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
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";

import type { AssignmentDetail, CourseInfo, Submission } from "./page";

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

// ─── Submission Row ───────────────────────────────────────────────────────────

function SubmissionRow({
  submission,
  isSelected,
  onSelect,
  onDetail,
}: {
  submission: Submission;
  isSelected: boolean;
  onSelect: () => void;
  onDetail: () => void;
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
      {/* Left — checkbox + info */}
      <div className="flex items-center gap-4">
        {/* Checkbox — only visible on hover or when selected */}
        <div className={`transition-opacity ${showCheckbox ? "opacity-100" : "opacity-0"}`}>
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

      {/* Right — similarity score (if available) + detail button */}
      <div className="flex items-center gap-3">
        {submission.similarity_score != null && (
          <span
            className={`text-lg font-bold tabular-nums ${
              submission.similarity_score >= 60
                ? "text-red-500"
                : submission.similarity_score >= 30
                ? "text-orange-400"
                : "text-emerald-500"
            }`}
          >
            {submission.similarity_score}%
          </span>
        )}
        <Button size="sm" variant="outline" onClick={onDetail} className="gap-1.5">
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

  const submissions = assignment.submissions;

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= 2) return prev; // max 2
        next.add(id);
      }
      return next;
    });
  };

  const handleCompare = () => {
    // Will be implemented when comparison API is ready
    const [id1, id2] = Array.from(selectedIds);
    console.log("Compare:", id1, id2);
  };

  const handleDetail = (submission: Submission) => {
    // Will be implemented — side-by-side code view
    console.log("Detail:", submission.submission_id);
  };

  const selectedCount = selectedIds.size;
  const canTriggerCompare = selectedCount === 2;

  // ── Stats ──────────────────────────────────────────────────────────────────
  const scoresWithValues = submissions
    .map((s) => s.similarity_score)
    .filter((s): s is number => s != null);

  const avgScore =
    scoresWithValues.length > 0
      ? Math.round(scoresWithValues.reduce((a, b) => a + b, 0) / scoresWithValues.length)
      : null;

  const highRisk = scoresWithValues.filter((s) => s >= 60).length;

  // ── Render ─────────────────────────────────────────────────────────────────

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
              {submissions.length} submission{submissions.length !== 1 ? "s" : ""}{" "}
              · Select exactly 2 to compare
            </p>
          </div>

          <Button
            onClick={handleCompare}
            disabled={!canTriggerCompare}
            className="gap-2"
          >
            <Code2 className="h-4 w-4" />
            Compare Selected
            {selectedCount > 0 && (
              <span className="ml-1 rounded-full bg-white/20 px-1.5 py-0.5 text-xs">
                {selectedCount}/2
              </span>
            )}
          </Button>
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
                isSelected={selectedIds.has(submission.submission_id)}
                onSelect={() => toggleSelect(submission.submission_id)}
                onDetail={() => handleDetail(submission)}
              />
            ))
          )}
        </div>
      </div>
    </main>
  );
}