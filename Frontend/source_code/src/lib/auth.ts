import { cookies } from "next/headers";
import { redirect } from "next/navigation";

type Role = "professor" | "student";

export async function requireRole(requiredRole: Role): Promise<string> {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) redirect("/");

  const res = await fetch(`${process.env.BACKEND_URL}/auth/role`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!res.ok) redirect("/");

  const data = await res.json();

  if (data.role !== requiredRole) {
    redirect(data.role === "professor" ? "/dashboard" : "/");
  }

  return token;
}