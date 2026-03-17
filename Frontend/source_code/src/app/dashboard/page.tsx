import { redirect } from "next/navigation";
import { DashboardClient } from "./DashboardClient";
import type { Course } from "./types";
import { requireRole } from "@/lib/auth";
import { Metadata } from "next";
import { openGraphShared } from "../shared-metadata";

export const metadata: Metadata = {
  title: "Dashboard",
  description:
    "View and manage your courses and assignments. Access detailed analytics and similarity reports for each assignment. Create new courses and assignments to start detecting code plagiarism.",
  alternates: {
    canonical: "/dashboard",
  },
  openGraph: {
    ...openGraphShared,
    url: "/dashboard",
  },
};

async function getAllCoursesWithAssignments(token: string): Promise<Course[]> {
  // First fetch the course list
  const res = await fetch(`${process.env.BACKEND_URL}/courses/`, {
    headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (res.status === 401) redirect("/");
  if (!res.ok) throw new Error("Failed to fetch courses.");

  const data = await res.json();
  const courses: Course[] = data.courses ?? [];

  // Then fetch all course details (with assignments) in parallel
  const detailed = await Promise.all(
    courses.map((course) =>
      fetch(`${process.env.BACKEND_URL}/courses/${course.course_id}`, {
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      }).then((r) => {
        if (r.status === 401) redirect("/");
        return r.json() as Promise<Course>;
      }),
    ),
  );

  return detailed;
}

export default async function DashboardPage() {
  const token = await requireRole("professor");
  const courses = await getAllCoursesWithAssignments(token);

  return <DashboardClient initialCourses={courses} />;
}
