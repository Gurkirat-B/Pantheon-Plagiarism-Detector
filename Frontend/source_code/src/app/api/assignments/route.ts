import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(req: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    const body = await req.json();

    const res = await fetch(`${process.env.BACKEND_URL}/assignments/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        course_id: body.course_id,
        title: body.title,
        language: body.language,
        due_date: body.due_date,
        settings: {},
      }),
    });

    const data = await res.json();

    if (res.status === 401) {
      return NextResponse.json({ message: data.detail }, { status: 401 });
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Failed to create assignment." },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 201 });
  } catch {
    return NextResponse.json({ message: "Internal server error." }, { status: 500 });
  }
}