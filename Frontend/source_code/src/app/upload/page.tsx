import FileUpload from "@/components/forms/FileUpload";
import { requireRole } from "@/lib/auth";
import { Metadata } from "next";
import { openGraphShared } from "../shared-metadata";

export const metadata: Metadata = {
  title: "Upload Submission",
  description:
    "Submit your programming assignment for plagiarism detection. Upload a zip file containing your code, and our system will analyze it against other submissions to ensure academic integrity. Get detailed similarity reports and insights after the analysis is complete.",
  alternates: {
    canonical: "/upload",
  },
  openGraph: {
    ...openGraphShared,
    url: "/upload",
  },
};

export default async function UploadPage() {
  await requireRole("student");
  return (
    <main>
      <section
        aria-labelledby="hero-section"
        className="flex flex-col items-center justify-center gap-12 p-24 px-8 sm:gap-10 lg:m-auto lg:max-w-screen-xl 2xl:max-w-screen-2xl"
      >
        <h1 className="text-center text-5xl font-bold xl:text-6xl">
          Submit Assignment
        </h1>
        <FileUpload />
      </section>
    </main>
  );
}
