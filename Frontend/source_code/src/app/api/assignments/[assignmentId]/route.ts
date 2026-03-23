import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ assignmentId: string }> },
) {
  try {
    const { assignmentId } = await params;
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json(
        { message: "Not authenticated." },
        { status: 401 },
      );
    }

    const res = await fetch(
      `${process.env.BACKEND_URL}/assignments/${assignmentId}`,
      {
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );

    const data = await res.json();

    if (res.status === 401) {
      return NextResponse.json({ message: data.detail }, { status: 401 });
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Failed to fetch course." },
        { status: res.status },
      );
    }

    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { message: "Internal server error." },
      { status: 500 },
    );
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ assignmentId: string }> },
) {
  try {
    const { assignmentId } = await params;
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json(
        { message: "Not authenticated." },
        { status: 401 },
      );
    }

    const body = await req.json();

    const res = await fetch(
      `${process.env.BACKEND_URL}/assignments/${assignmentId}`,
      {
        method: "PUT",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      },
    );

    if (res.status === 401) {
      const data = await res.json();
      return NextResponse.json({ message: data.detail }, { status: 401 });
    }

    if (res.status === 422) {
      const data = await res.json();
      return NextResponse.json(
        { message: "Validation error.", detail: data.detail },
        { status: 422 },
      );
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Failed to update assignment." },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { message: "Internal server error." },
      { status: 500 },
    );
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ assignmentId: string }> },
) {
  try {
    const { assignmentId } = await params;
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json(
        { message: "Not authenticated." },
        { status: 401 },
      );
    }

    const res = await fetch(
      `${process.env.BACKEND_URL}/assignments/${assignmentId}`,
      {
        method: "DELETE",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (res.status === 401) {
      const data = await res.json();
      return NextResponse.json({ message: data.detail }, { status: 401 });
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Failed to delete assignment." },
        { status: res.status },
      );
    }

    return new NextResponse(null, { status: 204 });
  } catch {
    return NextResponse.json(
      { message: "Internal server error." },
      { status: 500 },
    );
  }
}
