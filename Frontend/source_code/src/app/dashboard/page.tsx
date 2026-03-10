"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Eye,
  EyeOff,
  Pencil,
  Trash2,
  Plus,
  Users,
  ClipboardList,
  ArrowRight,
  MoreHorizontal,
  CheckCircle2,
  Clock,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

function AssignmentRow({
  assignment,
  onReview,
  onEdit,
  onDelete,
  onToggleHidden,
}: {
  assignment: Assignment;
  onReview: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggleHidden: () => void;
}) {
  const fullyAnalyzed =
    assignment.submissions > 0 &&
    assignment.analyzed === assignment.submissions;

  return (
    <div
      className={`flex items-center justify-between rounded-lg border px-5 py-4 transition-colors ${
        assignment.hidden
          ? "border-dashed bg-muted/40 opacity-60"
          : "bg-white hover:bg-slate-50"
      }`}
    >
      {/* Left info */}
      <div className="flex items-start gap-4">
        <span className="mt-0.5 min-w-[2.5rem] rounded-md bg-slate-100 px-2 py-0.5 text-center text-xs font-semibold text-slate-600">
          {assignment.code}
        </span>
        <div>
          <div className="flex items-center gap-2">
            <p className="font-medium text-slate-800">{assignment.title}</p>
            {assignment.hidden && (
              <Badge
                variant="outline"
                className="text-xs text-muted-foreground"
              >
                Hidden
              </Badge>
            )}
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
        <Button
          size="sm"
          onClick={onReview}
          className="gap-1.5"
        >
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
            <DropdownMenuItem onClick={onToggleHidden}>
              {assignment.hidden ? (
                <>
                  <Eye className="mr-2 h-4 w-4" />
                  Show assignment
                </>
              ) : (
                <>
                  <EyeOff className="mr-2 h-4 w-4" />
                  Hide assignment
                </>
              )}
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

  const handleToggleHidden = (courseId: string, assignmentId: string) => {
    setCourses((prev) =>
      prev.map((course) =>
        course.id !== courseId
          ? course
          : {
              ...course,
              assignments: course.assignments.map((a) =>
                a.id !== assignmentId ? a : { ...a, hidden: !a.hidden },
              ),
            },
      ),
    );
  };

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
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses.map((course) => {
          const isSelected = course.id === selectedCourseId;
          return (
            <Card
              key={course.id}
              onClick={() => setSelectedCourseId(course.id)}
              className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                isSelected
                  ? "border-2 border-slate-800 shadow-md"
                  : "border hover:border-slate-300"
              }`}
            >
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
      </div>
      {selectedCourse && (
        <div className="mt-8 rounded-xl border bg-white shadow-sm">
          {/* Section header */}
          <div className="flex items-center justify-between px-6 py-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">
                Assignments —{" "}
                <span className="text-slate-500">{selectedCourse.name}</span>
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {selectedCourse.assignments.filter((a) => !a.hidden).length}{" "}
                visible ·{" "}
                {selectedCourse.assignments.filter((a) => a.hidden).length}{" "}
                hidden
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
                  onToggleHidden={() =>
                    handleToggleHidden(selectedCourse.id, assignment.id)
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
    </main>
  );
}
