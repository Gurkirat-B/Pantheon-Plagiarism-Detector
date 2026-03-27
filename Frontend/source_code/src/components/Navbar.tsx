/* eslint-disable @next/next/no-img-element */
import Link from "next/link";
import { cookies } from "next/headers";
import { LogoutButton } from "./LogoutButton";
import { AccountButton } from "./AccountButton";

export default async function Navbar() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  const isLoggedIn = !!token;

  let isProfessor = false;
  let professorName = "";
  let professorEmail = "";

  if (token) {
    const res = await fetch(`${process.env.BACKEND_URL}/auth/role`, {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    if (res.ok) {
      const data = await res.json();
      isProfessor = data.role === "professor";
      professorName = "John Doe";
      professorEmail = "example@example.com";
    }
  }

  return (
    <header className="border-b border-slate-200 bg-background">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 p-5 min-[2000px]:max-w-[2000px]">
        <div className="flex items-center gap-5">
          <Link href="/" className="flex items-start gap-3">
            <div className="w-fit">
              <img
                src="/logo.png"
                alt="Pantheon Logo"
                className="h-12 w-auto"
              />
            </div>
          </Link>
        </div>
        <div className="flex items-center justify-center gap-5">
          {isLoggedIn && isProfessor && (
            <AccountButton name={professorName} email={professorEmail} />
          )}
          {isLoggedIn && <LogoutButton />}
        </div>
      </div>
    </header>
  );
}
