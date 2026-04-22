import { Shield, BarChart3, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function AboutUsPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-6 pt-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-5 py-2.5 text-sm font-medium text-foreground shadow-sm transition-all duration-200 hover:bg-muted hover:shadow-none"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>
      </div>

      <section className="relative mx-auto max-w-4xl px-6 pb-8 pt-12 text-center">
        {/* Eyebrow pill */}
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted px-4 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[#d40f0d]" />
          <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Our Mission
          </span>
        </div>

        <h1 className="text-5xl font-bold tracking-tight text-foreground sm:text-6xl">
          About{" "}
          <span>
            <span className="text-foreground">Pan</span>
            <span className="text-[#d40f0d]">theon</span>
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
          <span className="font-semibold text-foreground">
            Welcome to Pantheon!
          </span>{" "}
          We are a small, dedicated development team committed to upholding
          academic honesty through cutting-edge technology.
        </p>

        {/* Decorative divider */}
        <div className="mx-auto mt-10 flex items-center justify-center gap-3">
          <div className="h-px w-16 bg-border" />
          <div className="h-1.5 w-1.5 rounded-full bg-[#d40f0d]" />
          <div className="h-px w-16 bg-border" />
        </div>
      </section>

      {/* ── Feature cards ── */}
      <section className="relative mx-auto max-w-5xl px-6 py-14">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Card 1 — Advanced Plagiarism Detection */}
          <div className="group relative overflow-hidden rounded-2xl border border-border bg-card p-8 shadow-sm transition-shadow duration-300 hover:shadow-md">
            {/* Corner accent */}
            <div className="absolute right-0 top-0 h-24 w-24 -translate-y-8 translate-x-8 rounded-full bg-[#d40f0d]/5 transition-transform duration-500 group-hover:scale-150" />

            {/* Icon */}
            <div className="relative mb-6 inline-flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-muted shadow-sm">
              <Shield className="h-7 w-7 text-foreground" strokeWidth={1.5} />
              <span className="absolute -right-1 -top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#d40f0d]">
                <span className="h-1.5 w-1.5 rounded-full bg-white" />
              </span>
            </div>

            <h2 className="mb-3 text-xl font-bold tracking-tight text-foreground">
              Advanced Plagiarism Detection
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Pantheon is an advanced code plagiarism detection system designed
              to identify similarities in source code with precision. Our
              platform analyzes code submissions to detect copied or unoriginal
              content, helping educators maintain academic standards.
            </p>

            {/* Bottom rule accent */}
            <div className="mt-8 h-px w-12 bg-[#d40f0d]/40 transition-all duration-300 group-hover:w-full group-hover:bg-[#d40f0d]/20" />
          </div>

          {/* Card 2 — Comprehensive Reporting */}
          <div className="group relative overflow-hidden rounded-2xl border border-border bg-card p-8 shadow-sm transition-shadow duration-300 hover:shadow-md">
            {/* Corner accent */}
            <div className="absolute right-0 top-0 h-24 w-24 -translate-y-8 translate-x-8 rounded-full bg-[#d40f0d]/5 transition-transform duration-500 group-hover:scale-150" />

            {/* Icon */}
            <div className="relative mb-6 inline-flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-muted shadow-sm">
              <BarChart3 className="h-7 w-7 text-foreground" strokeWidth={1.5} />
              <span className="absolute -right-1 -top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#d40f0d]">
                <span className="h-1.5 w-1.5 rounded-full bg-white" />
              </span>
            </div>

            <h2 className="mb-3 text-xl font-bold tracking-tight text-foreground">
              Comprehensive Reporting
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Our system provides detailed and insightful reports, giving
              educators the tools they need to understand and address potential
              plagiarism. We strive to make the process transparent and
              effective.
            </p>

            {/* Bottom rule accent */}
            <div className="mt-8 h-px w-12 bg-[#d40f0d]/40 transition-all duration-300 group-hover:w-full group-hover:bg-[#d40f0d]/20" />
          </div>
        </div>
      </section>

      {/* ── Closing statement ── */}
      <section className="relative mx-auto max-w-3xl px-6 pb-24 text-center">
        <div className="rounded-2xl border border-border bg-muted/50 px-8 py-10">
          {/* Large quote mark */}
          <div className="mb-2 select-none font-serif text-6xl leading-none text-[#d40f0d]/20">
            &quot;
          </div>
          <p className="text-lg font-medium italic text-muted-foreground">
            Dedicated to ensuring integrity and supporting academic success.
          </p>
          <div className="mx-auto mt-6 flex items-center justify-center gap-3">
            <div className="h-px w-10 bg-border" />
            <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              The Pantheon Team
            </span>
            <div className="h-px w-10 bg-border" />
          </div>
        </div>
      </section>
    </main>
  );
}
