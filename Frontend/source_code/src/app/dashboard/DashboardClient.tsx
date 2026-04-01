"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Pencil,
  Trash2,
  Plus,
  ClipboardList,
  ArrowRight,
  MoreHorizontal,
  Clock,
  BookOpen,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

import type { Course, Assignment } from "./types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingButton } from "@/components/LoadingButton";

// ─── Local form types ─────────────────────────────────────────────────────────

type EditAssignmentForm = { title: string; dueDate: string; language: string };

type EditCourseForm = {
  code: string;
  name: string;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr: string) {
  const [year, month, day] = dateStr.split("T")[0].split("-");
  return `${parseInt(month)}/${parseInt(day)}/${year}`;
}

// ─── Assignment Row ───────────────────────────────────────────────────────────

function AssignmentRow({
  assignment,
  onReview,
  onEdit,
  onDelete,
}: {
  assignment: Assignment;
  onReview: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border bg-white px-5 py-4 transition-colors hover:bg-slate-50">
      <div>
        <p className="font-medium text-slate-800">{assignment.title}</p>
        <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            Due {formatDate(assignment.due_date)}
          </span>
          <span>·</span>
          <span className="capitalize">
            {assignment.language === "cpp" ? "c++" : assignment.language}
          </span>
          <span>·</span>
          <span>Key: {assignment.assignment_id}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button size="sm" onClick={onReview} className="gap-1.5">
          Review
          <ArrowRight className="h-3.5 w-3.5" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit details
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onDelete}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete assignment
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

// ─── Dashboard Client ─────────────────────────────────────────────────────────

export function DashboardClient({
  initialCourses,
}: {
  initialCourses: Course[];
}) {
  const router = useRouter();

  const [courses, setCourses] = useState<Course[]>(initialCourses);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(
    initialCourses[0] ?? null,
  );

  // Assignment dialogs
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingAssignment, setEditingAssignment] = useState<{
    assignmentId: string;
    form: EditAssignmentForm;
  } | null>(null);
  const [editAssignmentError, setEditAssignmentError] = useState<string | null>(
    null,
  );
  const [isSavingAssignment, setIsSavingAssignment] = useState(false);
  const [editCourseError, setEditCourseError] = useState<string | null>(null);
  const [isSavingCourse, setIsSavingCourse] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingAssignment, setDeletingAssignment] = useState<{
    assignmentId: string;
    title: string;
  } | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState<EditAssignmentForm>({
    title: "",
    dueDate: "",
    language: "",
  });

  // Course dialogs
  const [editCourseDialogOpen, setEditCourseDialogOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<{
    courseId: string;
    form: EditCourseForm;
  } | null>(null);
  const [deleteCourseDialogOpen, setDeleteCourseDialogOpen] = useState(false);
  const [deletingCourse, setDeletingCourse] = useState<{
    courseId: string;
    name: string;
  } | null>(null);
  const [createCourseDialogOpen, setCreateCourseDialogOpen] = useState(false);
  const [createCourseForm, setCreateCourseForm] = useState<EditCourseForm>({
    code: "",
    name: "",
  });
  const [createCourseError, setCreateCourseError] = useState<string | null>(
    null,
  );
  const [createAssignmentError, setCreateAssignmentError] = useState<
    string | null
  >(null);
  const [deleteAssignmentError, setDeleteAssignmentError] = useState<
    string | null
  >(null);
  const [deleteCourseError, setDeleteCourseError] = useState<string | null>(
    null,
  );
  const [isCreatingAssignment, setIsCreatingAssignment] = useState(false);
  const [isCreatingCourse, setIsCreatingCourse] = useState(false);
  const [isDeletingAssignment, setIsDeletingAssignment] = useState(false);
  const [isDeletingCourse, setIsDeletingCourse] = useState(false);

  // ── Assignment handlers (optimistic — wire to API later) ──────────────────
  const handleSelectCourse = (courseId: string) => {
    const course = courses.find((c) => c.course_id === courseId) ?? null;
    setSelectedCourse(course);
  };

  const handleOpenEdit = (assignment: Assignment) => {
    setEditingAssignment({
      assignmentId: assignment.assignment_id,
      form: {
        title: assignment.title,
        language: assignment.language,
        dueDate: assignment.due_date.split("T")[0],
      },
    });
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingAssignment) return;
    setEditAssignmentError(null);
    setIsSavingAssignment(true);
    try {
      const res = await fetch(
        `/api/assignments/${editingAssignment.assignmentId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: editingAssignment.form.title,
            due_date: new Date(editingAssignment.form.dueDate).toISOString(),
            language: editingAssignment.form.language,
          }),
        },
      );

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      setSelectedCourse((prev) =>
        prev
          ? {
              ...prev,
              assignments: prev.assignments?.map((a) =>
                a.assignment_id !== editingAssignment.assignmentId
                  ? a
                  : {
                      ...a,
                      title: editingAssignment.form.title,
                      due_date: editingAssignment.form.dueDate,
                      language: editingAssignment.form.language,
                    },
              ),
            }
          : prev,
      );
      setCourses((prev) =>
        prev.map((c) =>
          c.course_id !== selectedCourse?.course_id
            ? c
            : {
                ...c,
                assignments: c.assignments?.map((a) =>
                  a.assignment_id !== editingAssignment.assignmentId
                    ? a
                    : {
                        ...a,
                        title: editingAssignment.form.title,
                        due_date: editingAssignment.form.dueDate,
                        language: editingAssignment.form.language,
                      },
                ),
              },
        ),
      );
      setEditDialogOpen(false);
    } catch {
      setEditAssignmentError("Failed to save changes. Please try again.");
    } finally {
      setIsSavingAssignment(false);
    }
  };

  const handleOpenDelete = (assignment: Assignment) => {
    setDeletingAssignment({
      assignmentId: assignment.assignment_id,
      title: assignment.title,
    });
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!deletingAssignment) return;
    setDeleteAssignmentError(null);
    setIsDeletingAssignment(true);
    try {
      const res = await fetch(
        `/api/assignments/${deletingAssignment.assignmentId}`,
        {
          method: "DELETE",
        },
      );

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      setSelectedCourse((prev) =>
        prev
          ? {
              ...prev,
              assignments: prev.assignments?.filter(
                (a) => a.assignment_id !== deletingAssignment.assignmentId,
              ),
            }
          : prev,
      );
      setCourses((prev) =>
        prev.map((c) =>
          c.course_id === selectedCourse?.course_id
            ? {
                ...c,
                assignments: c.assignments?.filter(
                  (a) => a.assignment_id !== deletingAssignment.assignmentId,
                ),
              }
            : c,
        ),
      );
      setDeleteDialogOpen(false);
    } catch {
      setDeleteAssignmentError(
        "Failed to delete assignment. Please try again.",
      );
    } finally {
      setIsDeletingAssignment(false);
    }
  };

  const handleCreateAssignment = async () => {
    if (
      !createForm.title ||
      !createForm.dueDate ||
      !createForm.language ||
      !selectedCourse
    )
      return;
    setCreateAssignmentError(null);
    setIsCreatingAssignment(true);
    try {
      const res = await fetch("/api/assignments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          course_id: selectedCourse.course_id,
          title: createForm.title,
          language: createForm.language,
          due_date: new Date(createForm.dueDate).toISOString(),
        }),
      });

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      const newAssignment: Assignment = await res.json();
      setSelectedCourse((prev) =>
        prev
          ? {
              ...prev,
              assignments: [...(prev.assignments ?? []), newAssignment],
            }
          : prev,
      );
      setCourses((prev) =>
        prev.map((c) =>
          c.course_id === selectedCourse.course_id
            ? { ...c, assignments: [...(c.assignments ?? []), newAssignment] }
            : c,
        ),
      );
      setCreateForm({ title: "", dueDate: "", language: "" });
      setCreateDialogOpen(false);
    } catch {
      setCreateAssignmentError(
        "Failed to create assignment. Please try again.",
      );
    } finally {
      setIsCreatingAssignment(false);
    }
  };

  // ── Course handlers (optimistic — wire to API later) ──────────────────────

  const handleOpenEditCourse = (course: Course) => {
    setEditingCourse({
      courseId: course.course_id,
      form: { code: String(course.code), name: course.name },
    });
    setEditCourseDialogOpen(true);
  };

  const handleSaveEditCourse = async () => {
    if (!editingCourse) return;
    setEditCourseError(null);
    setIsSavingCourse(true);
    try {
      const res = await fetch(`/api/courses/${editingCourse.courseId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: editingCourse.form.code,
          name: editingCourse.form.name,
        }),
      });

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      setCourses((prev) =>
        prev.map((c) =>
          c.course_id !== editingCourse.courseId
            ? c
            : {
                ...c,
                code: editingCourse.form.code,
                name: editingCourse.form.name,
              },
        ),
      );
      if (selectedCourse?.course_id === editingCourse.courseId) {
        setSelectedCourse((prev) =>
          prev
            ? {
                ...prev,
                code: editingCourse.form.code,
                name: editingCourse.form.name,
              }
            : prev,
        );
      }
      setEditCourseDialogOpen(false);
    } catch {
      setEditCourseError("Failed to save changes. Please try again.");
    } finally {
      setIsSavingCourse(false);
    }
  };

  const handleOpenDeleteCourse = (course: Course) => {
    setDeletingCourse({ courseId: course.course_id, name: course.name });
    setDeleteCourseDialogOpen(true);
  };

  const handleConfirmDeleteCourse = async () => {
    if (!deletingCourse) return;
    setDeleteCourseError(null);
    setIsDeletingCourse(true);
    try {
      const res = await fetch(`/api/courses/${deletingCourse.courseId}`, {
        method: "DELETE",
      });

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      const remaining = courses.filter(
        (c) => c.course_id !== deletingCourse.courseId,
      );
      setCourses(remaining);
      if (selectedCourse?.course_id === deletingCourse.courseId) {
        setSelectedCourse(remaining[0] ?? null);
      }
      setDeleteCourseDialogOpen(false);
    } catch {
      setDeleteCourseError("Failed to delete course. Please try again.");
    } finally {
      setIsDeletingCourse(false);
    }
  };

  const handleCreateCourse = async () => {
    if (!createCourseForm.code || !createCourseForm.name) return;
    setCreateCourseError(null);
    setIsCreatingCourse(true);
    try {
      const res = await fetch("/api/courses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: createCourseForm.code,
          name: createCourseForm.name,
        }),
      });

      if (res.status === 401) {
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error();

      const newCourse: Course = await res.json();
      setCourses((prev) => [...prev, { ...newCourse, assignments: [] }]);
      setSelectedCourse({ ...newCourse, assignments: [] });
      setCreateCourseForm({ code: "", name: "" });
      setCreateCourseDialogOpen(false);
    } catch {
      setCreateCourseError("Failed to create course. Please try again.");
    } finally {
      setIsCreatingCourse(false);
    }
  };
  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-10 min-[2000px]:max-w-[2000px]">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Dashboard
        </h1>
        <p className="mt-1 text-muted-foreground">
          Review submissions and manage your courses
        </p>
      </div>

      {/* Courses header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Your Courses</h2>
          <p className="text-sm text-muted-foreground">
            {courses.length} course{courses.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button
          onClick={() => setCreateCourseDialogOpen(true)}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          New Course
        </Button>
      </div>

      {/* Course Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => {
          const isSelected = selectedCourse?.course_id === course.course_id;
          return (
            <Card
              key={course.course_id}
              onClick={() => handleSelectCourse(course.course_id)}
              className={`group relative cursor-pointer transition-all duration-200 hover:shadow-md ${
                isSelected
                  ? "border-2 border-slate-800 shadow-md"
                  : "border hover:border-slate-300"
              }`}
            >
              <div
                className="absolute right-3 top-3"
                onClick={(e) => e.stopPropagation()}
              >
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => handleOpenEditCourse(course)}
                    >
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit course
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleOpenDeleteCourse(course)}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete course
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-slate-800">
                  {course.name}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Code: {course.code}
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <ClipboardList className="h-4 w-4" />
                  {course.assignments?.length ?? "—"} assignments
                </div>
              </CardContent>
            </Card>
          );
        })}

        {courses.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center text-muted-foreground">
            <BookOpen className="mb-3 h-8 w-8 opacity-40" />
            <p className="font-medium">No courses yet</p>
            <p className="mt-1 text-sm">
              Create your first course to get started
            </p>
          </div>
        )}
      </div>

      {/* Assignments Section */}
      {selectedCourse && (
        <div className="mt-8 rounded-xl border bg-white shadow-sm">
          <div className="flex items-center justify-between px-6 py-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">
                Assignments —{" "}
                <span className="text-slate-500">{selectedCourse.name}</span>
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {selectedCourse.assignments?.length ?? 0} assignment
                {(selectedCourse.assignments?.length ?? 0) !== 1 ? "s" : ""}
              </p>
            </div>
            <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              New Assignment
            </Button>
          </div>

          <Separator />

          <div className="space-y-3 p-6">
            {(selectedCourse.assignments?.length ?? 0) === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                No assignments yet. Create one to get started.
              </div>
            ) : (
              selectedCourse.assignments?.map((assignment) => (
                <AssignmentRow
                  key={assignment.assignment_id}
                  assignment={assignment}
                  onReview={() =>
                    router.push(
                      `/dashboard/assignments/${assignment.assignment_id}`,
                    )
                  }
                  onEdit={() => handleOpenEdit(assignment)}
                  onDelete={() => handleOpenDelete(assignment)}
                />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Edit Assignment Dialog ──────────────────────────────────────────── */}
      <Dialog
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) setEditAssignmentError(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Assignment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="mb-1.5 block text-sm">Title</Label>
              <Input
                placeholder="Assignment title"
                value={editingAssignment?.form.title ?? ""}
                onChange={(e) =>
                  setEditingAssignment((prev) =>
                    prev
                      ? {
                          ...prev,
                          form: { ...prev.form, title: e.target.value },
                        }
                      : prev,
                  )
                }
              />
            </div>
            <div>
              <Label className="mb-1.5 block text-sm">Language</Label>
              <Select
                value={editingAssignment?.form.language ?? ""}
                onValueChange={(value) =>
                  setEditingAssignment((prev) =>
                    prev
                      ? { ...prev, form: { ...prev.form, language: value } }
                      : prev,
                  )
                }
              >
                <SelectTrigger className="mt-1.5 w-full">
                  <SelectValue placeholder="Select a language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="c">C</SelectItem>
                  <SelectItem value="cpp">C++</SelectItem>
                  <SelectItem value="java">Java</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 block text-sm">Due Date</Label>
              <Input
                type="date"
                value={editingAssignment?.form.dueDate ?? ""}
                onChange={(e) =>
                  setEditingAssignment((prev) =>
                    prev
                      ? {
                          ...prev,
                          form: { ...prev.form, dueDate: e.target.value },
                        }
                      : prev,
                  )
                }
              />
            </div>
            {editAssignmentError && (
              <p className="text-sm text-destructive">{editAssignmentError}</p>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <LoadingButton
              loading={isSavingAssignment}
              onClick={handleSaveEdit}
              disabled={
                !editingAssignment?.form.title ||
                !editingAssignment?.form.dueDate ||
                !editingAssignment?.form.language
              }
            >
              Save changes
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Create Assignment Dialog ────────────────────────────────────────── */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Assignment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="mb-1.5 block text-sm">Title</Label>
              <Input
                placeholder="Assignment title"
                value={createForm.title}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, title: e.target.value }))
                }
              />
            </div>
            <div>
              <Label className="mb-1.5 block text-sm">Language</Label>
              <Select
                value={createForm.language}
                onValueChange={(value) =>
                  setCreateForm((prev) => ({ ...prev, language: value }))
                }
              >
                <SelectTrigger className="mt-1.5 w-full">
                  <SelectValue placeholder="Select a language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="c">C</SelectItem>
                  <SelectItem value="cpp">C++</SelectItem>
                  <SelectItem value="java">Java</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 block text-sm">Due Date</Label>
              <Input
                type="date"
                value={createForm.dueDate}
                onChange={(e) =>
                  setCreateForm((prev) => ({
                    ...prev,
                    dueDate: e.target.value,
                  }))
                }
              />
            </div>
            {createAssignmentError && (
              <p className="text-sm text-destructive">
                {createAssignmentError}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setCreateForm({ title: "", dueDate: "", language: "" });
                setCreateAssignmentError(null);
                setCreateDialogOpen(false);
              }}
            >
              Cancel
            </Button>
            <LoadingButton
              loading={isCreatingAssignment}
              onClick={handleCreateAssignment}
              disabled={
                !createForm.title || !createForm.dueDate || !createForm.language
              }
            >
              Create
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Assignment Confirmation ──────────────────────────────────── */}
      <AlertDialog
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          setDeleteDialogOpen(open);
          if (!open) setDeleteAssignmentError(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete assignment?</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{deletingAssignment?.title}</strong> and all its
              submission data will be permanently deleted. This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteAssignmentError && (
            <p className="text-sm text-destructive">{deleteAssignmentError}</p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <LoadingButton
              loading={isDeletingAssignment}
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </LoadingButton>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Edit Course Dialog ──────────────────────────────────────────────── */}
      <Dialog
        open={editCourseDialogOpen}
        onOpenChange={(open) => {
          setEditCourseDialogOpen(open);
          if (!open) setEditCourseError(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Course</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="mb-1.5 block text-sm">Course Code</Label>
              <Input
                placeholder="COSC 1P01"
                value={editingCourse?.form.code ?? ""}
                onChange={(e) =>
                  setEditingCourse((prev) =>
                    prev
                      ? {
                          ...prev,
                          form: { ...prev.form, code: e.target.value },
                        }
                      : prev,
                  )
                }
              />
            </div>
            <div>
              <Label className="mb-1.5 block text-sm">Course Name</Label>
              <Input
                placeholder="Introduction to Computer Science"
                value={editingCourse?.form.name ?? ""}
                onChange={(e) =>
                  setEditingCourse((prev) =>
                    prev
                      ? {
                          ...prev,
                          form: { ...prev.form, name: e.target.value },
                        }
                      : prev,
                  )
                }
              />
            </div>
            {editCourseError && (
              <p className="text-sm text-destructive">{editCourseError}</p>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <LoadingButton
              loading={isSavingCourse}
              onClick={handleSaveEditCourse}
              disabled={!editingCourse?.form.code || !editingCourse?.form.name}
            >
              Save changes
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Create Course Dialog ────────────────────────────────────────────── */}
      <Dialog
        open={createCourseDialogOpen}
        onOpenChange={setCreateCourseDialogOpen}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Course</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="mb-1.5 block text-sm">Course Code</Label>
              <Input
                placeholder="COSC 1P01"
                value={createCourseForm.code}
                onChange={(e) =>
                  setCreateCourseForm((prev) => ({
                    ...prev,
                    code: e.target.value,
                  }))
                }
              />
            </div>
            <div>
              <Label className="mb-1.5 block text-sm">Course Name</Label>
              <Input
                placeholder="Introduction to Computer Science"
                value={createCourseForm.name}
                onChange={(e) =>
                  setCreateCourseForm((prev) => ({
                    ...prev,
                    name: e.target.value,
                  }))
                }
              />
            </div>
            {createCourseError && (
              <p className="text-sm text-destructive">{createCourseError}</p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setCreateCourseForm({ code: "", name: "" });
                setCreateCourseError(null);
                setCreateCourseDialogOpen(false);
              }}
            >
              Cancel
            </Button>
            <LoadingButton
              loading={isCreatingCourse}
              onClick={handleCreateCourse}
            >
              Create
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Course Confirmation ──────────────────────────────────────── */}
      <AlertDialog
        open={deleteCourseDialogOpen}
        onOpenChange={(open) => {
          setDeleteCourseDialogOpen(open);
          if (!open) setDeleteCourseError(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete course?</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{deletingCourse?.name}</strong> and all its assignments
              will be permanently deleted. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteCourseError && (
            <p className="text-sm text-destructive">{deleteCourseError}</p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <LoadingButton
              loading={isDeletingCourse}
              onClick={handleConfirmDeleteCourse}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </LoadingButton>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
