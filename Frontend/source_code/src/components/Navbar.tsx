import Link from "next/link";
import { cookies } from "next/headers";
import { LogoutButton } from "./LogoutButton";

export default async function Navbar() {
  const cookieStore = await cookies();
  const isLoggedIn = !!cookieStore.get("access_token")?.value;

  return (
    <header className="bg-background shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 p-5 min-[2000px]:max-w-[2000px]">
        <div className="flex items-center gap-5">
          <Link href="/" className="flex items-start gap-3">
            <div className="text-3xl font-semibold 2xl:text-4xl">
              <span className="text-black">Pan</span>
              <span className="text-[#d40f0d]">theon</span>
            </div>
          </Link>
        </div>
        <div className="flex items-center justify-center gap-5">
          {isLoggedIn && <LogoutButton />}
        </div>
      </div>
    </header>
  );
}