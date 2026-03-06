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
          submissions: 45,
          analyzed: 45,
          hidden: false,
        },
        {
          id: "a2",
          code: "A2",
          title: "Array Operations",
          dueDate: "2024-09-30",
          submissions: 43,
          analyzed: 43,
          hidden: false,
        },
        {
          id: "a3",
          code: "A3",
          title: "String Manipulation",
          dueDate: "2024-10-19",
          submissions: 12,
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
          hidden: true,
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