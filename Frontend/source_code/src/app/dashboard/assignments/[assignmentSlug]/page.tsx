import {
  getAssignmentById,
  getCourseByAssignmentId,
  getSubmissionsByAssignment,
} from "@/app/dashboard/data";
import { AssignmentView } from "./AssignmentView";

export default async function AssignmentPage({
  params,
}: {
  params: Promise<{ assignmentSlug: string }>;
}) {
  const { assignmentSlug } = await params;

  const assignment = getAssignmentById(assignmentSlug);
  const course = getCourseByAssignmentId(assignmentSlug);
  const submissions = getSubmissionsByAssignment(assignmentSlug);

  if (!assignment || !course) {
    return (
      <main className="mx-auto min-h-screen max-w-7xl px-6 py-10 min-[2000px]:max-w-[2000px]">
        <p className="text-muted-foreground">Assignment not found.</p>
      </main>
    );
  }

  return (
    <AssignmentView
      assignment={assignment}
      course={course}
      submissions={submissions}
    />
  );
}
