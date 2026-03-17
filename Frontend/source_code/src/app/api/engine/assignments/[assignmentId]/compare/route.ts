import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ assignmentId: string }> }
) {
  try {
    const { assignmentId } = await params;
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    const body = await req.json();

    const res = await fetch(
      `${process.env.BACKEND_URL}/engine/assignments/${assignmentId}/compare`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          submission_a_id: body.submission_a_id,
          submission_b_id: body.submission_b_id,
        }),
      }
    );

    if (res.status === 401) {
      const data = await res.json();
      return NextResponse.json({ message: data.detail }, { status: 401 });
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Comparison failed. Please try again." },
        { status: res.status }
      );
    }

    // Backend now returns JSON — forward directly
    const data = await res.json();
    return NextResponse.json(data, { status: 200 });
  } catch {
    return NextResponse.json({ message: "Internal server error." }, { status: 500 });
  }
}