"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Pencil,
  Trash2,
  Plus,
  Users,
  ClipboardList,
  ArrowRight,
  MoreHorizontal,
  CheckCircle2,
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
  AlertDialogAction,
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
import { dashboardData, type Course, type Assignment } from "./data";
import { formatDate } from "@/lib/utils";

type EditAssignmentForm = {
  code: string;
  title: string;
  dueDate: string;
};

type EditCourseForm = {
  code: string;
  name: string;
};

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
  const fullyAnalyzed =
    assignment.submissions > 0 &&
    assignment.analyzed === assignment.submissions;

  return (
    <div className="flex items-center justify-between rounded-lg border bg-white px-5 py-4 transition-colors hover:bg-slate-50">
      {/* Left info */}
      <div className="flex items-start gap-4">
        <span className="mt-0.5 min-w-[2.5rem] rounded-md bg-slate-100 px-2 py-0.5 text-center text-xs font-semibold text-slate-600">
          {assignment.code}
        </span>
        <div>
          <div className="flex items-center gap-2">
            <p className="font-medium text-slate-800">{assignment.title}</p>
            {fullyAnalyzed && (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            )}
          </div>
          <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              Due {formatDate(assignment.dueDate)}
            </span>
            <span>·</span>
            <span>{assignment.submissions} submissions</span>
            <span>·</span>
            <span>{assignment.analyzed} analyzed</span>
          </div>
        </div>
      </div>

      {/* Right actions */}
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

export default function DashboardPage() {
  const router = useRouter();

  const [courses, setCourses] = useState<Course[]>(dashboardData.courses);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(
    dashboardData.courses[0]?.id ?? "",
  );

  // Course edit dialog
  const [editCourseDialogOpen, setEditCourseDialogOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<{
    courseId: string;
    form: EditCourseForm;
  } | null>(null);

  // Course delete dialog
  const [deleteCourseDialogOpen, setDeleteCourseDialogOpen] = useState(false);
  const [deletingCourse, setDeletingCourse] = useState<{
    courseId: string;
    name: string;
  } | null>(null);

  // Course create dialog
  const [createCourseDialogOpen, setCreateCourseDialogOpen] = useState(false);
  const [createCourseForm, setCreateCourseForm] = useState<EditCourseForm>({
    code: "",
    name: "",
  });

  // Edit dialog
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingAssignment, setEditingAssignment] = useState<{
    courseId: string;
    assignmentId: string;
    form: EditAssignmentForm;
  } | null>(null);

  // Delete dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingAssignment, setDeletingAssignment] = useState<{
    courseId: string;
    assignmentId: string;
    title: string;
  } | null>(null);

  // Create dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState<EditAssignmentForm>({
    code: "",
    title: "",
    dueDate: "",
  });

  const selectedCourse = courses.find((c) => c.id === selectedCourseId);

  const handleOpenEdit = (courseId: string, assignment: Assignment) => {
    setEditingAssignment({
      courseId,
      assignmentId: assignment.id,
      form: {
        code: assignment.code,
        title: assignment.title,
        dueDate: assignment.dueDate,
      },
    });
    setEditDialogOpen(true);
  };

  const handleSaveEdit = () => {
    if (!editingAssignment) return;
    setCourses((prev) =>
      prev.map((course) =>
        course.id !== editingAssignment.courseId
          ? course
          : {
              ...course,
              assignments: course.assignments.map((a) =>
                a.id !== editingAssignment.assignmentId
                  ? a
                  : {
                      ...a,
                      code: editingAssignment.form.code,
                      title: editingAssignment.form.title,
                      dueDate: editingAssignment.form.dueDate,
                    },
              ),
            },
      ),
    );
    setEditDialogOpen(false);
  };

  const handleOpenDelete = (
    courseId: string,
    assignmentId: string,
    title: string,
  ) => {
    setDeletingAssignment({ courseId, assignmentId, title });
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (!deletingAssignment) return;
    setCourses((prev) =>
      prev.map((course) =>
        course.id !== deletingAssignment.courseId
          ? course
          : {
              ...course,
              assignments: course.assignments.filter(
                (a) => a.id !== deletingAssignment.assignmentId,
              ),
            },
      ),
    );
    setDeleteDialogOpen(false);
  };

  const handleCreateAssignment = () => {
    if (!selectedCourse || !createForm.title || !createForm.dueDate) return;
    const newAssignment: Assignment = {
      id: `a-${Date.now()}`,
      code: createForm.code || `A${selectedCourse.assignments.length + 1}`,
      title: createForm.title,
      dueDate: createForm.dueDate,
      submissions: 0,
      analyzed: 0,
      hidden: false,
    };
    setCourses((prev) =>
      prev.map((course) =>
        course.id !== selectedCourseId
          ? course
          : { ...course, assignments: [...course.assignments, newAssignment] },
      ),
    );
    setCreateForm({ code: "", title: "", dueDate: "" });
    setCreateDialogOpen(false);
  };

  const handleOpenEditCourse = (course: Course) => {
    setEditingCourse({
      courseId: course.id,
      form: { code: course.code, name: course.name },
    });
    setEditCourseDialogOpen(true);
  };

  const handleSaveEditCourse = () => {
    if (!editingCourse) return;
    setCourses((prev) =>
      prev.map((c) =>
        c.id !== editingCourse.courseId
          ? c
          : {
              ...c,
              code: editingCourse.form.code,
              name: editingCourse.form.name,
            },
      ),
    );
    setEditCourseDialogOpen(false);
  };

  const handleOpenDeleteCourse = (course: Course) => {
    setDeletingCourse({ courseId: course.id, name: course.name });
    setDeleteCourseDialogOpen(true);
  };

  const handleConfirmDeleteCourse = () => {
    if (!deletingCourse) return;
    setCourses((prev) => prev.filter((c) => c.id !== deletingCourse.courseId));
    // If deleted course was selected, fall back to first remaining
    if (selectedCourseId === deletingCourse.courseId) {
      setCourses((prev) => {
        const remaining = prev.filter((c) => c.id !== deletingCourse.courseId);
        setSelectedCourseId(remaining[0]?.id ?? "");
        return remaining;
      });
    }
    setDeleteCourseDialogOpen(false);
  };

  const handleCreateCourse = () => {
    if (!createCourseForm.code || !createCourseForm.name) return;
    const newCourse: Course = {
      id: `course-${Date.now()}`,
      code: createCourseForm.code,
      name: createCourseForm.name,
      students: 0,
      assignments: [],
    };
    setCourses((prev) => [...prev, newCourse]);
    setSelectedCourseId(newCourse.id);
    setCreateCourseForm({ code: "", name: "" });
    setCreateCourseDialogOpen(false);
  };

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-10 min-[2000px]:max-w-[2000px]">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Welcome, {dashboardData.instructor}!
        </h1>
        <p className="mt-1 text-muted-foreground">
          Review submissions and manage your courses
        </p>
      </div>
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
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => {
          const isSelected = course.id === selectedCourseId;
          return (
            <Card
              key={course.id}
              onClick={() => setSelectedCourseId(course.id)}
              className={`group relative cursor-pointer transition-all duration-200 hover:shadow-md ${
                isSelected
                  ? "border-2 border-slate-800 shadow-md"
                  : "border hover:border-slate-300"
              }`}
            >
              {/* Course actions — stop propagation so card click doesn't fire */}
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
                  {course.code}
                </CardTitle>
                <p className="text-sm text-muted-foreground">{course.name}</p>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Users className="h-4 w-4" />
                    {course.students} students
                  </span>
                  <span className="flex items-center gap-1.5">
                    <ClipboardList className="h-4 w-4" />
                    {course.assignments.length} assignments
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}

        {/* Empty state */}
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
      {selectedCourse && (
        <div className="mt-8 rounded-xl border bg-white shadow-sm">
          {/* Section header */}
          <div className="flex items-center justify-between px-6 py-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">
                Assignments -{" "}
                <span className="text-slate-500">{selectedCourse.name}</span>
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {selectedCourse.assignments.length} assignment
                {selectedCourse.assignments.length !== 1 ? "s" : ""}
              </p>
            </div>
            <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              New Assignment
            </Button>
          </div>

          <Separator />
          <div className="space-y-3 p-6">
            {selectedCourse.assignments.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                No assignments yet. Create one to get started.
              </div>
            ) : (
              selectedCourse.assignments.map((assignment) => (
                <AssignmentRow
                  key={assignment.id}
                  assignment={assignment}
                  onReview={() =>
                    router.push(`/dashboard/assignments/${assignment.id}`)
                  }
                  onEdit={() => handleOpenEdit(selectedCourse.id, assignment)}
                  onDelete={() =>
                    handleOpenDelete(
                      selectedCourse.id,
                      assignment.id,
                      assignment.title,
                    )
                  }
                />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Edit Assignment Dialog ────────────────────────────────────────── */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Assignment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="mb-1.5 block text-sm">Code</Label>
                <Input
                  placeholder="A1"
                  value={editingAssignment?.form.code ?? ""}
                  onChange={(e) =>
                    setEditingAssignment((prev) =>
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
              <div className="col-span-2">
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
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleSaveEdit}>Save changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Create Assignment Dialog ──────────────────────────────────────── */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Assignment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="mb-1.5 block text-sm">Code</Label>
                <Input
                  placeholder="A1"
                  value={createForm.code}
                  onChange={(e) =>
                    setCreateForm((prev) => ({ ...prev, code: e.target.value }))
                  }
                />
              </div>
              <div className="col-span-2">
                <Label className="mb-1.5 block text-sm">Title</Label>
                <Input
                  placeholder="Assignment title"
                  value={createForm.title}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      title: e.target.value,
                    }))
                  }
                />
              </div>
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
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              onClick={handleCreateAssignment}
              disabled={!createForm.title || !createForm.dueDate}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Confirmation ───────────────────────────────────────────── */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete assignment?</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{deletingAssignment?.title}</strong> and all its
              submission data will be permanently deleted. This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Edit Course Dialog ───────────────────────────────────────────── */}
      <Dialog
        open={editCourseDialogOpen}
        onOpenChange={setEditCourseDialogOpen}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Course</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="mb-1.5 block text-sm">Course Code</Label>
              <Input
                placeholder="COSC-101"
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
                placeholder="Introduction to Programming"
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
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              onClick={handleSaveEditCourse}
              disabled={!editingCourse?.form.code || !editingCourse?.form.name}
            >
              Save changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Create Course Dialog ──────────────────────────────────────────── */}
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
                placeholder="COSC-101"
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
                placeholder="Introduction to Programming"
                value={createCourseForm.name}
                onChange={(e) =>
                  setCreateCourseForm((prev) => ({
                    ...prev,
                    name: e.target.value,
                  }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              onClick={handleCreateCourse}
              disabled={!createCourseForm.code || !createCourseForm.name}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Course Confirmation ────────────────────────────────────── */}
      <AlertDialog
        open={deleteCourseDialogOpen}
        onOpenChange={setDeleteCourseDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete course?</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{deletingCourse?.name}</strong> and all its assignments
              will be permanently deleted. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDeleteCourse}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
