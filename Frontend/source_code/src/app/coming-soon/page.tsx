import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function ComingSoonPage() {
  return (
    <main className="relative flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center overflow-hidden bg-background px-6">
      {/* Subtle grid texture */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(currentColor 1px, transparent 1px), linear-gradient(90deg, currentColor 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* Red accent blobs */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#d40f0d] opacity-[0.04] blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-0 h-72 w-72 -translate-y-1/3 translate-x-1/3 rounded-full bg-[#d40f0d] opacity-[0.06] blur-2xl" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center">
        {/* Eyebrow */}
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted px-3.5 py-1.5">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#d40f0d]" />
          <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            In progress
          </span>
        </div>

        {/* Headline */}
        <h1 className="text-[clamp(3.5rem,12vw,9rem)] font-bold leading-none tracking-tighter text-foreground">
          Coming
          <br />
          <span className="text-[#d40f0d]">Soon</span>
        </h1>

        {/* Sub-copy */}
        <p className="mt-8 max-w-sm text-base text-muted-foreground">
          This page is still being built. Check back later — it&apos;ll be worth it.
        </p>

        {/* Back link */}
        <Link
          href="/"
          className="mt-10 inline-flex items-center gap-2 rounded-full border border-border bg-background px-5 py-2.5 text-sm font-medium text-foreground shadow-sm transition-all duration-200 hover:bg-muted hover:shadow-none"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>
      </div>

      {/* Bottom rule */}
      <div className="absolute bottom-10 left-1/2 flex -translate-x-1/2 items-center gap-3">
        <div className="h-px w-16 bg-border" />
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60">
          Pantheon
        </span>
        <div className="h-px w-16 bg-border" />
      </div>
    </main>
  );
}
