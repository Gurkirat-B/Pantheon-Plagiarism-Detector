import { notFound, redirect } from "next/navigation";
import { AssignmentView } from "./AssignmentView";
import { requireRole } from "@/lib/auth";
import { Metadata } from "next";
import { openGraphShared } from "@/app/shared-metadata";

// ─── Types ────────────────────────────────────────────────────────────────────

export type Submission = {
  submission_id: string;
  user_id: string;
  email: string;
  original_zip_name: string;
  submitted_at: string;
  s3_bucket: string;
  s3_key: string;
  similarity_score?: number | null;
  has_comparison: boolean;
};

export type AssignmentDetail = {
  assignment_id: string;
  course_id: string;
  title: string;
  language: string;
  due_date: string;
  settings: Record<string, unknown>;
  created_at: string;
  submissions: Submission[];
};

export type CourseInfo = {
  course_id: string;
  code: number;
  name: string;
};

// Matches the actual API response shape from GET /engine/similarity-report-student?submission_id=
export type SimilarityReport = {
  // Submission identifiers (camelCase as returned by API)
  submissionA: string;
  submissionB: string;
  // Score is 0–100 scale
  similarityScore: number;
  similarityLevel: string;
  language: string;
  // Full report detail fields
  matches: RawMatch[];
  fullCodeA: string;
  fullCodeB: string;
  fileOffsetsA: Record<string, number>;
  fileOffsetsB: Record<string, number>;
  identicalSubmissions: boolean;
  High: number;
  Medium: number;
  Low: number;
  sections: number;
  alterationTechniquesDetected: string[];
};

export type RawMatch = {
  codeA: string;
  codeB: string;
  fileA: string;
  fileB: string;
  index: number;
  linesA: number[];
  linesB: number[];
  severity: string;
  lineHighlightsA: number[];
  lineHighlightsB: number[];
};

// ─── Fetchers ─────────────────────────────────────────────────────────────────

async function getAssignment(
  token: string,
  assignmentId: string,
): Promise<AssignmentDetail | null> {
  const res = await fetch(
    `${process.env.BACKEND_URL}/assignments/${assignmentId}`,
    {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    },
  );

  if (res.status === 401) redirect("/");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch assignment.");

  return res.json();
}

async function getCourse(token: string, courseId: string): Promise<CourseInfo> {
  const res = await fetch(`${process.env.BACKEND_URL}/courses/${courseId}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (res.status === 401) redirect("/");
  if (!res.ok) throw new Error("Failed to fetch course.");

  return res.json();
}

async function getReports(
  token: string,
  submissions: Submission[],
): Promise<SimilarityReport[]> {
  if (submissions.length === 0) return [];
  const withComparisons = submissions.filter((s) => s.has_comparison);
  if (withComparisons.length === 0) return [];

  const batches = await Promise.all(
    withComparisons.map(async (s) => {
      const res = await fetch(
        `${process.env.BACKEND_URL}/engine/similarity-report-student?submission_id=${s.submission_id}`,
        {
          headers: {
            Accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
          cache: "no-store",
        },
      );
      if (res.status === 401) redirect("/");
      // 404 means no reports yet — treat as empty
      if (res.status === 404 || !res.ok) return [] as SimilarityReport[];
      const data = await res.json();
      // API may return a single object or an array
      return (Array.isArray(data) ? data : [data]) as SimilarityReport[];
    }),
  );

  // Flatten and deduplicate by submissionA+submissionB pair
  const seen = new Set<string>();
  const all: SimilarityReport[] = [];
  for (const batch of batches) {
    if (!Array.isArray(batch)) continue;
    for (const report of batch) {
      // Normalise the key so A+B and B+A are treated as the same pair
      const ids = [report.submissionA, report.submissionB].sort();
      const key = ids.join("_");
      if (!seen.has(key)) {
        seen.add(key);
        all.push(report);
      }
    }
  }
  return all;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ assignmentSlug: string }>;
}): Promise<Metadata> {
  const { assignmentSlug } = await params;
  const token = await requireRole("professor");
  const assignment = await getAssignment(token, assignmentSlug);
  if (assignment === null) notFound();
  const url = `/dashboard/assignments/${assignmentSlug}`;
  return {
    title: assignment.title,
    description:
      "View detailed analytics and similarity reports for the assignment. Manage submissions, review plagiarism results, and access comprehensive insights to ensure academic integrity.",
    alternates: {
      canonical: url,
    },
    openGraph: {
      ...openGraphShared,
      url: url,
    },
  };
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function AssignmentPage({
  params,
}: {
  params: Promise<{ assignmentSlug: string }>;
}) {
  const { assignmentSlug } = await params;
  const token = await requireRole("professor");

  const assignment = await getAssignment(token, assignmentSlug);
  if (assignment === null) notFound();

  const [course, initialReports] = await Promise.all([
    getCourse(token, assignment.course_id),
    getReports(token, assignment.submissions),
  ]);

  return (
    <AssignmentView
      assignment={assignment}
      course={course}
      initialReports={initialReports}
    />
  );
}
