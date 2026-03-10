import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    console.log(`${process.env.BACKEND_URL}/auth/register`);
    const res = await fetch(`${process.env.BACKEND_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    // Forward 409 conflict back to the client
    if (res.status === 409) {
      return NextResponse.json(
        { message: data.detail },
        { status: 409 }
      );
    }

    if (!res.ok) {
      return NextResponse.json(
        { message: "Registration failed. Please try again." },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 201 });
  } catch {
    return NextResponse.json(
      { message: "Internal server error." },
      { status: 500 }
    );
  }
}