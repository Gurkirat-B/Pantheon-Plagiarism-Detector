import { Metadata } from "next";
import { openGraphShared } from "@/app/shared-metadata";
import MainForm from "@/components/forms/MainForm";
import { redirectIfAuthenticated } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Pantheon Code Plagiarism Detector",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    ...openGraphShared,
    url: "/",
  },
};

export default async function HomePage() {
  await redirectIfAuthenticated();
  return (
    <main>
      <section
        aria-labelledby="hero-section"
        className="flex flex-col items-center justify-center gap-12 p-24 px-8 sm:gap-14 lg:m-auto lg:h-[calc(100vh-76px)] lg:max-w-screen-xl lg:flex-row lg:gap-20 2xl:max-w-screen-2xl"
      >
        <div className="flex flex-col items-center gap-12 lg:basis-1/2 lg:items-start lg:gap-10">
          <h1
            id="hero-section"
            className="text-center text-5xl font-bold sm:text-4xl lg:text-left xl:text-6xl 2xl:text-7xl"
          >
            Pantheon Code Plagiarism Detector
          </h1>
          <p className="m-auto max-w-lg text-center text-lg lg:m-0 lg:max-w-none lg:text-left">
            Web-based plagiarism detection system for academic programming
            assignments. Analyze code submissions against repositories with
            advanced similarity detection, comprehensive reporting, and
            privacy-first design.
          </p>
        </div>
        <MainForm />
      </section>
    </main>
  );
}
