"use client";
import { useToast } from "@/hooks/use-toast";
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
import { delay } from "@/lib/utils";
import ToggleFormButton from "./ToggleFormButton";

const email = z
  .string()
  .trim()
  .min(3, "Email must be at least 3 characters.")
  .email("Please type a valid email.");
const password = z
  .string()
  .min(6, { message: "Password must be at least 6 characters long." })
  .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$/, {
    message: "Password must contain lowercase, uppercase, and number.",
  });

const loginFormSchema = z.object({
  email: email,
  password: password,
});

type FormState = "student" | "instructor";

interface LoginFormProps {
  activeForm: FormState;
  onSwitch: (value: FormState) => void;
}

export default function LoginForm({ activeForm, onSwitch }: LoginFormProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const loginForm = useForm<z.infer<typeof loginFormSchema>>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  async function onSubmit(values: z.infer<typeof loginFormSchema>) {
    try {
      setLoading(true);
      toast({ description: "Email: ".concat(values.email as string) });
      await delay(3000);
    } catch (error) {
      console.error("Form submission error", error);
      toast({
        variant: "destructive",
        description: "Failed to submit the form. Please try again.",
      });
    }
  }

  return (
    <Form {...loginForm}>
      <form
        onSubmit={loginForm.handleSubmit(onSubmit)}
        className="mx-auto max-w-3xl space-y-7 rounded-2xl px-7 py-10 shadow-[0px_0px_30px_rgba(0,44,122,0.13)] sm:px-10"
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

        <LoadingButton
          loading={loading}
          className="w-full px-10 py-6 text-base capitalize lg:py-7 lg:text-lg"
          type="submit"
        >
          Sign In as Instructor
        </LoadingButton>

      </form>
    </Form>
  );
}
