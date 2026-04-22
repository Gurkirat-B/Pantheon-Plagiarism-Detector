"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { LoadingButton } from "../LoadingButton";
import { useState } from "react";
import ToggleFormButton from "./ToggleFormButton";
import { useRouter } from "next/navigation";

const studentFormSchema = z.object({
  email: z
    .string()
    .trim()
    .min(3, "Email must be at least 3 characters.")
    .email("Please type a valid email."),
  key: z.string().trim().min(3, "Key must be at least 3 characters."),
});

type FormState = "student" | "instructor";

interface StudentFormProps {
  activeForm: FormState;
  onSwitch: (value: FormState) => void;
}

export default function StudentForm({
  activeForm,
  onSwitch,
}: StudentFormProps) {
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const studentForm = useForm<z.infer<typeof studentFormSchema>>({
    resolver: zodResolver(studentFormSchema),
    defaultValues: {
      email: "",
      key: "",
    },
  });

  async function onSubmit(values: z.infer<typeof studentFormSchema>) {
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: values.email,
          assignment_id: values.key,
          role: "student",
        }),
      });
      const result = await res.json();
      if (!res.ok) {
        studentForm.setError("root", {
          type: "manual",
          message: result.message,
        });
        return;
      }
      sessionStorage.setItem("assignmentKey", values.key);
      router.push("/upload");
      router.refresh();
    } catch {
      studentForm.setError("root", {
        type: "manual",
        message: "Something went wrong. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Form {...studentForm}>
      <form
        onSubmit={studentForm.handleSubmit(onSubmit)}
        className="mx-auto max-w-3xl space-y-7 rounded-2xl bg-white px-7 py-10 shadow-[0px_0px_30px_rgba(0,44,122,0.13)] dark:bg-zinc-900 sm:px-10"
      >
        <div className="flex w-full flex-col gap-2 text-center">
          <div className="text-2xl font-bold lg:text-3xl">Welcome Student</div>
          <p className="text-base text-muted-foreground">
            Enter your email and the assignment key provided by your instructor
          </p>
        </div>
        <ToggleFormButton
          activeForm={activeForm}
          onSwitch={(value) => onSwitch(value)}
        />
        <FormField
          control={studentForm.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-base sm:text-lg">Email</FormLabel>
              <FormControl>
                <Input
                  id="email"
                  placeholder="student@example.com"
                  type="email"
                  autoComplete="email"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={studentForm.control}
          name="key"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-base sm:text-lg">
                Assignment Key
              </FormLabel>
              <FormControl>
                <Input
                  id="key"
                  placeholder="Assignment Key"
                  autoComplete="off"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {studentForm.formState.errors.root && (
          <p className="text-sm text-destructive">
            {studentForm.formState.errors.root.message}
          </p>
        )}
        <LoadingButton
          loading={loading}
          className="w-full px-10 py-6 text-base capitalize lg:py-7 lg:text-lg"
          type="submit"
        >
          Sign In
        </LoadingButton>
      </form>
    </Form>
  );
}
