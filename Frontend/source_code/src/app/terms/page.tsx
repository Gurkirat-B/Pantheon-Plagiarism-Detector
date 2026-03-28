import { ScrollText } from "lucide-react";

const SECTIONS = [
  {
    number: "01",
    title: "Acceptance of Terms",
    content: (
      <p>
        By accessing and using our service, you accept and agree to be bound by
        these terms and conditions.
      </p>
    ),
  },
  {
    number: "02",
    title: "Use of Service",
    content: (
      <ul>
        <li>Our service is intended solely for detecting plagiarism in code.</li>
        <li>
          You agree not to misuse the service or attempt to access it in an
          unauthorized manner.
        </li>
      </ul>
    ),
  },
  {
    number: "03",
    title: "User Responsibilities",
    content: (
      <ul>
        <li>You are responsible for the code you submit for analysis.</li>
        <li>
          You must ensure that you have the right to check the code for
          plagiarism.
        </li>
        <li>You agree not to submit any malicious or illegal content.</li>
      </ul>
    ),
  },
  {
    number: "04",
    title: "Privacy and Data Security",
    content: (
      <ul>
        <li>We respect your privacy and protect your submitted code.</li>
        <li>Data is processed securely and confidentially.</li>
      </ul>
    ),
  },
  {
    number: "05",
    title: "Limitation of Liability",
    content: (
      <ul>
        <li>
          We are not liable for any damages resulting from the use of our
          service.
        </li>
      </ul>
    ),
  },
  {
    number: "06",
    title: "Changes to Terms",
    content: (
      <ul>
        <li>
          We may update these terms at any time. Continued use of the service
          means you accept the new terms.
        </li>
      </ul>
    ),
  },
];

export default function TermsPage() {
  return (
    <main className="relative min-h-screen bg-white">
      <section className="mx-auto max-w-3xl px-6 pb-10 pt-16 text-center">
        <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 shadow-sm">
          <ScrollText className="h-5 w-5 text-slate-700" strokeWidth={1.5} />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Terms &amp; Conditions
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-slate-500">
          Welcome to our Code Plagiarism Detection Service. By using our
          services, you agree to the following terms and conditions.
        </p>
        <div className="mx-auto mt-8 flex items-center justify-center gap-3">
          <div className="h-px w-12 bg-slate-200" />
          <div className="h-1.5 w-1.5 rounded-full bg-[#d40f0d]" />
          <div className="h-px w-12 bg-slate-200" />
        </div>
      </section>

      {/* Sections */}
      <section className="mx-auto max-w-3xl px-6 pb-20">
        <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white shadow-sm">
          {SECTIONS.map((section) => (
            <div
              key={section.number}
              className="group px-8 py-7 transition-colors duration-150 hover:bg-slate-50/70"
            >
              <div className="flex items-start gap-5">
                {/* Number badge */}
                <span className="mt-0.5 shrink-0 font-mono text-xs font-bold tabular-nums text-[#d40f0d]/60">
                  {section.number}
                </span>

                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-bold text-slate-800">
                    {section.title}
                  </h2>
                  <div className="mt-3 text-sm leading-relaxed text-slate-500 [&_li]:mt-2 [&_li]:flex [&_li]:items-start [&_li]:gap-2.5 [&_li]:before:mt-1.5 [&_li]:before:h-1.5 [&_li]:before:w-1.5 [&_li]:before:shrink-0 [&_li]:before:rounded-full [&_li]:before:bg-[#d40f0d]/50 [&_p]:text-slate-500 [&_ul]:space-y-0.5">
                    {section.content}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer note */}
        <div className="mt-10 rounded-xl border border-slate-200 bg-slate-50 px-8 py-6 text-center">
          <p className="text-sm text-slate-500">
            If you have any questions about these terms,{" "}
            <a
              href="#"
              className="font-semibold text-slate-800 underline underline-offset-2 transition-colors hover:text-[#d40f0d]"
            >
              please contact us
            </a>
            .
          </p>
        </div>
      </section>
    </main>
  );
}