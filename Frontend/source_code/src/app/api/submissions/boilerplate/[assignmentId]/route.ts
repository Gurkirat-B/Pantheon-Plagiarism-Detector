import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ assignmentId: string }> },
) {
  try {
    const { assignmentId } = await params;
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    const formData = await req.formData();
    const file = formData.get("file");
    if (!file) {
      return NextResponse.json({ message: "No file provided." }, { status: 400 });
    }

    const backendForm = new FormData();
    backendForm.append("file", file);

    const res = await fetch(
      `${process.env.BACKEND_URL}/submissions/boilerplate/${assignmentId}`,
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

    if (res.status === 401) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: data.message ?? data.detail ?? "Upload failed." },
        { status: res.status },
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch {
    return NextResponse.json({ message: "Internal server error." }, { status: 500 });
  }
}
