import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(req: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("access_token")?.value;

    if (!token) {
      return NextResponse.json(
        { message: "Not authenticated." },
        { status: 401 },
      );
    }

    const { searchParams } = new URL(req.url);
    const submissionIds = (searchParams.get("submission_ids") ?? "")
      .split(",")
      .filter(Boolean);

    if (submissionIds.length === 0) {
      return NextResponse.json([]);
    }

    // Fan out one request per submission ID in parallel
    const batches = await Promise.all(
      submissionIds.map(async (id) => {
        const res = await fetch(
          `${process.env.BACKEND_URL}/engine/similarity-report?submission_id=${id}`,
          {
            headers: {
              Accept: "application/json",
              Authorization: `Bearer ${token}`,
            },
          },
        );
        if (res.status === 401) return null; // signal auth failure
        if (!res.ok) return [];
        return res.json();
      }),
    );

    // Propagate auth failure
    if (batches.some((b) => b === null)) {
      return NextResponse.json(
        { message: "Not authenticated." },
        { status: 401 },
      );
    }

    // Flatten and deduplicate by report_id
    const seen = new Set<string>();
    const all: unknown[] = [];
    for (const batch of batches as unknown[][]) {
      if (!Array.isArray(batch)) continue;
      for (const report of batch) {
        const r = report as { submissionA?: string; submissionB?: string };
        const ids = [r.submissionA ?? "", r.submissionB ?? ""].sort();
        const key = ids.join("_");
        if (!seen.has(key)) {
          seen.add(key);
          all.push(report);
        }
      }
    }

    return NextResponse.json(all, { status: 200 });
  } catch {
    return NextResponse.json(
      { message: "Internal server error." },
      { status: 500 },
    );
  }
}
