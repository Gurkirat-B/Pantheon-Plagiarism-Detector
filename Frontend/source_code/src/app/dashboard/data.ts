export type Assignment = {
  id: string;
  code: string; // e.g. "A1"
  title: string;
  dueDate: string;
  submissions: number;
  analyzed: number;
  hidden: boolean;
};

export type Course = {
  id: string;
  code: string;
  name: string;
  students: number;
  assignments: Assignment[];
};

export type Submission = {
  id: string;
  assignmentId: string;
  studentId: string;
  fileName: string;
  submittedAt: string;
  similarityScore: number; // 0–100
  mostSimilarSubmissionId: string;
  code: string;
};

export const dashboardData: {
  instructor: string;
  courses: Course[];
} = {
  instructor: "Batman",
  courses: [
    {
      id: "course-1",
      code: "COSC-101",
      name: "Introduction to Programming",
      students: 45,
      assignments: [
        {
          id: "a1",
          code: "A1",
          title: "Hello World Program",
          dueDate: "2024-09-14",
          submissions: 2,
          analyzed: 2,
          hidden: false,
        },
        {
          id: "a2",
          code: "A2",
          title: "Array Operations",
          dueDate: "2024-09-30",
          submissions: 5,
          analyzed: 5,
          hidden: false,
        },
        {
          id: "a3",
          code: "A3",
          title: "String Manipulation",
          dueDate: "2024-10-19",
          submissions: 0,
          analyzed: 0,
          hidden: false,
        },
      ],
    },
    {
      id: "course-2",
      code: "COSC-201",
      name: "Data Structures and Algorithms",
      students: 38,
      assignments: [
        {
          id: "a4",
          code: "A1",
          title: "Linked List Implementation",
          dueDate: "2024-09-20",
          submissions: 38,
          analyzed: 38,
          hidden: false,
        },
        {
          id: "a5",
          code: "A2",
          title: "Binary Search Tree",
          dueDate: "2024-10-10",
          submissions: 30,
          analyzed: 20,
          hidden: false,
        },
      ],
    },
    {
      id: "course-3",
      code: "COSC-310",
      name: "Software Engineering",
      students: 29,
      assignments: [
        {
          id: "a6",
          code: "A1",
          title: "Requirements Document",
          dueDate: "2024-09-25",
          submissions: 29,
          analyzed: 29,
          hidden: false,
        },
        {
          id: "a7",
          code: "A2",
          title: "UML Diagrams",
          dueDate: "2024-10-15",
          submissions: 15,
          analyzed: 10,
          hidden: false,
        },
        {
          id: "a8",
          code: "A3",
          title: "Sprint Planning Report",
          dueDate: "2024-11-01",
          submissions: 0,
          analyzed: 0,
          hidden: false,
        },
      ],
    },
  ],
};

export const submissionsData: Submission[] = [
  // Assignment a2 — Array Operations
  {
    id: "sub-1",
    assignmentId: "a2",
    studentId: "STU-67C2D",
    fileName: "arrays.c",
    submittedAt: "2024-09-30T11:30:00",
    similarityScore: 65,
    mostSimilarSubmissionId: "sub-2",
    code: `#include <stdio.h>

int main() {
    int arr[5] = {1, 2, 3, 4, 5};
    int sum = 0;

    for(int i = 0; i < 5; i++) {
        sum += arr[i];
    }

    printf("Sum: %d\\n", sum);
    return 0;
}`,
  },
  {
    id: "sub-2",
    assignmentId: "a2",
    studentId: "STU-89E4F",
    fileName: "assignment2.c",
    submittedAt: "2024-10-01T06:15:00",
    similarityScore: 38,
    mostSimilarSubmissionId: "sub-1",
    code: `#include <stdio.h>

int main() {
    int numbers[5] = {1, 2, 3, 4, 5};
    int total = 0;

    for(int i = 0; i < 5; i++) {
        total += numbers[i];
    }

    printf("Total: %d\\n", total);
    return 0;
}`,
  },
  {
    id: "sub-3",
    assignmentId: "a2",
    studentId: "STU-45A3B",
    fileName: "array_ops.c",
    submittedAt: "2024-09-30T10:20:00",
    similarityScore: 12,
    mostSimilarSubmissionId: "sub-1",
    code: `#include <stdio.h>
#include <stdlib.h>

#define SIZE 5

void printArray(int* arr, int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\\n");
}

int sumArray(int* arr, int n) {
    int result = 0;
    for (int i = 0; i < n; i++) {
        result += arr[i];
    }
    return result;
}

int main() {
    int data[SIZE] = {10, 20, 30, 40, 50};
    printArray(data, SIZE);
    printf("Sum: %d\\n", sumArray(data, SIZE));
    return 0;
}`,
  },
  {
    id: "sub-4",
    assignmentId: "a2",
    studentId: "STU-12F9A",
    fileName: "hw2.c",
    submittedAt: "2024-09-29T22:05:00",
    similarityScore: 82,
    mostSimilarSubmissionId: "sub-1",
    code: `#include <stdio.h>

int main() {
    int arr[5] = {1, 2, 3, 4, 5};
    int s = 0;

    for(int i = 0; i < 5; i++) {
        s += arr[i];
    }

    printf("Sum: %d\\n", s);
    return 0;
}`,
  },
  {
    id: "sub-5",
    assignmentId: "a2",
    studentId: "STU-33B7C",
    fileName: "solution.c",
    submittedAt: "2024-09-30T09:45:00",
    similarityScore: 21,
    mostSimilarSubmissionId: "sub-3",
    code: `#include <stdio.h>

int main(void) {
    int values[] = {5, 10, 15, 20, 25};
    int len = sizeof(values) / sizeof(values[0]);
    int accumulator = 0;

    for (int idx = 0; idx < len; idx++) {
        accumulator = accumulator + values[idx];
    }

    printf("The total sum is: %d\\n", accumulator);
    return 0;
}`,
  },
  // Assignment a1 — Hello World
  {
    id: "sub-6",
    assignmentId: "a1",
    studentId: "STU-67C2D",
    fileName: "main.c",
    submittedAt: "2024-09-14T08:00:00",
    similarityScore: 55,
    mostSimilarSubmissionId: "sub-7",
    code: `#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}`,
  },
  {
    id: "sub-7",
    assignmentId: "a1",
    studentId: "STU-89E4F",
    fileName: "hello.c",
    submittedAt: "2024-09-13T14:30:00",
    similarityScore: 55,
    mostSimilarSubmissionId: "sub-6",
    code: `#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}`,
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function getSubmissionsByAssignment(assignmentId: string): Submission[] {
  return submissionsData.filter((s) => s.assignmentId === assignmentId);
}

export function getSubmissionById(id: string): Submission | undefined {
  return submissionsData.find((s) => s.id === id);
}

export function getAssignmentById(id: string): Assignment | undefined {
  for (const course of dashboardData.courses) {
    const found = course.assignments.find((a) => a.id === id);
    if (found) return found;
  }
  return undefined;
}

export function getCourseByAssignmentId(assignmentId: string): Course | undefined {
  return dashboardData.courses.find((course) =>
    course.assignments.some((a) => a.id === assignmentId)
  );
}