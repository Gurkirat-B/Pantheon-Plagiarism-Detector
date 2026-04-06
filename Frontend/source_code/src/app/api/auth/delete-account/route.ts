import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function DELETE(req: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json({ message: "Not authenticated." }, { status: 401 });
    }

    const body = await req.json();
    const res = await fetch(`${process.env.BACKEND_URL}/auth/delete-account`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json(
        { message: data.message ?? "Failed to delete account." },
        { status: res.status },
      );
    }

    const response = NextResponse.json({ success: true }, { status: 200 });
    response.cookies.delete("access_token");
    return response;
  } catch {
    return NextResponse.json({ message: "Internal server error." }, { status: 500 });
  }
}
