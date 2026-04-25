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
import { PasswordInput } from "@/components/ui/password-input";
import { LoadingButton } from "../LoadingButton";
import { useState } from "react";
import ToggleFormButton from "./ToggleFormButton";
import { loginFormSchema } from "./formSchema";
import SignUpForm from "./SignUpForm";
import { useRouter } from "next/navigation";

type FormState = "student" | "instructor";

interface LoginFormProps {
  activeForm: FormState;
  onSwitch: (value: FormState) => void;
}

export default function LoginForm({ activeForm, onSwitch }: LoginFormProps) {
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const loginForm = useForm<z.infer<typeof loginFormSchema>>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  async function onSubmit(data: z.infer<typeof loginFormSchema>) {
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          role: "professor",
        }),
      });

      const result = await res.json();

      if (res.status === 401) {
        loginForm.setError("root", {
          type: "manual",
          message: result.message,
        });
        return;
      }

      if (!res.ok) {
        loginForm.setError("root", {
          type: "manual",
          message: result.message,
        });
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch {
      loginForm.setError("root", {
        type: "manual",
        message: "Something went wrong. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Form {...loginForm}>
      <form
        onSubmit={loginForm.handleSubmit(onSubmit)}
        className="mx-auto max-w-3xl space-y-7 rounded-2xl bg-white px-7 py-10 shadow-[0px_0px_30px_rgba(0,44,122,0.13)] dark:bg-zinc-900 sm:px-10"
      >
        <div className="flex w-full flex-col gap-2 text-center">
          <div className="text-2xl font-bold lg:text-3xl">Welcome Back</div>
          <p className="text-base text-muted-foreground">
            Sign in to access your account
          </p>
        </div>
        <ToggleFormButton
          activeForm={activeForm}
          onSwitch={(value) => onSwitch(value)}
        />
        <FormField
          control={loginForm.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-base sm:text-lg">Email</FormLabel>
              <FormControl>
                <Input
                  id="email"
                  placeholder="instructor@example.com"
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
          control={loginForm.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel htmlFor="password" className="text-base sm:text-lg">
                Password
              </FormLabel>
              <FormControl>
                <PasswordInput
                  id="password"
                  placeholder="•••••••"
                  autoComplete="current-password"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {loginForm.formState.errors.root && (
          <p className="text-sm text-destructive">
            {loginForm.formState.errors.root.message}
          </p>
        )}
        <LoadingButton
          loading={loading}
          className="w-full px-10 py-6 text-base capitalize lg:py-7 lg:text-lg"
          type="submit"
        >
          Sign In as Instructor
        </LoadingButton>
        <div className="text-base">
          <p>
            New User? <SignUpForm />
          </p>
        </div>
      </form>
    </Form>
  );
}
