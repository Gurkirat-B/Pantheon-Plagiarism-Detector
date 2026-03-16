import FileUpload from "@/components/forms/FileUpload";
import { requireRole } from "@/lib/auth";

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
