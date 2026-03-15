import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ assignmentKey: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) {
    return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
  }

  const { assignmentKey } = await params;
  const formData = await req.formData();
  const file = formData.get("file");
  if (!file) {
    return NextResponse.json({ message: "No file provided." }, { status: 400 });
  }

  const backendForm = new FormData();
  backendForm.append("file", file);

  const res = await fetch(
    `${process.env.BACKEND_URL}/submissions/${assignmentKey}`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: backendForm,
    },
  );

  const data = await res.json();

  if (!res.ok) {
    return NextResponse.json(
      { message: data.message ?? "Submission failed." },
      { status: res.status },
    );
  }

  return NextResponse.json(data, { status: 200 });
}
