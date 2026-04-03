import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ assignmentId: string }> },
) {
  try {
    const { assignmentId } = await params;
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    const res = await fetch(
      `${process.env.BACKEND_URL}/engine/assignments/${assignmentId}/compare-repo`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (res.status === 401) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    if (res.status === 400) {
      return NextResponse.json({ message: "Invalid assignment ID" }, { status: 400 });
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Repository comparison failed. Please try again." },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 200 });
  } catch {
    return NextResponse.json({ message: "Internal server error." }, { status: 500 });
  }
}
