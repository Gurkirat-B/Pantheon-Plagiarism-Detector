export type Assignment = {
  assignment_id: string;
  title: string;
  language: string;
  due_date: string;
  created_at: string;
};

export type Course = {
  course_id: string;
  code: number;
  name: string;
  assignments?: Assignment[];
};