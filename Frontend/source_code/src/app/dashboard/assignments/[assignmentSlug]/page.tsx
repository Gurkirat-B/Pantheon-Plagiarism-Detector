import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AssignmentView } from "./AssignmentView";

// ─── Types ────────────────────────────────────────────────────────────────────

export type Submission = {
  submission_id: string;
  user_id: string;
  email: string;
  original_zip_name: string;
  submitted_at: string;
  status: string;
  s3_bucket: string;
  s3_key: string;
  similarity_score?: number | null; // present only after comparison
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

// ─── Fetchers ─────────────────────────────────────────────────────────────────

async function getAssignment(
  token: string,
  assignmentId: string
): Promise<AssignmentDetail> {
  const res = await fetch(
    `${process.env.BACKEND_URL}/assignments/${assignmentId}`,
    {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (res.status === 401) redirect("/");
  if (!res.ok) throw new Error("Failed to fetch assignment.");

  return res.json();
}

async function getCourse(
  token: string,
  courseId: string
): Promise<CourseInfo> {
  const res = await fetch(
    `${process.env.BACKEND_URL}/courses/${courseId}`,
    {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  if (res.status === 401) redirect("/");
  if (!res.ok) throw new Error("Failed to fetch course.");

  return res.json();
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function AssignmentPage({
  params,
}: {
  params: Promise<{ assignmentSlug: string }>;
}) {
  const { assignmentSlug } = await params;

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) redirect("/");

  // Fetch assignment first, then course in parallel
  const assignment = await getAssignment(token, assignmentSlug);
  const course = await getCourse(token, assignment.course_id);

  return <AssignmentView assignment={assignment} course={course} />;
}