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
import { LoadingButton } from "../LoadingButton";
import { useState } from "react";
import { delay } from "@/lib/utils";
import ToggleFormButton from "./ToggleFormButton";
import { useRouter } from "next/navigation";

const key = z.string().trim().min(3, "Key must be at least 3 characters.");

const studentFormSchema = z.object({
  key: key,
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
  const { toast } = useToast();
  const router = useRouter();
  const studentForm = useForm<z.infer<typeof studentFormSchema>>({
    resolver: zodResolver(studentFormSchema),
    defaultValues: {
      key: "",
    },
  });

  // function onSubmit(values: z.infer<typeof formSchema>) {
  //   try {
  //     fetch("https://formsubmit.co/ajax/f57f135f6f3011863d0d0df3158180bd", {
  //       method: "POST",
  //       headers: {
  //         "Content-Type": "application/json",
  //         Accept: "application/json",
  //       },
  //       body: JSON.stringify(values),
  //     })
  //       .then((response) => response.json())
  //       .then((data) => console.log(data))
  //       .catch((error) => console.log(error));
  //     toast({ description: "Submit form successfully!" });
  //   } catch (error) {
  //     console.error("Form submission error", error);
  //     toast({
  //       variant: "destructive",
  //       description: "Failed to submit the form. Please try again.",
  //     });
  //   }
  // }
  async function onSubmit(values: z.infer<typeof studentFormSchema>) {
    try {
      setLoading(true);
      toast({ description: "Key: ".concat(values.key as string) });
      await delay(3000);
      router.push("/upload")
    } catch (error) {
      console.error("Form submission error", error);
      toast({
        variant: "destructive",
        description: "Failed to submit the form. Please try again.",
      });
    }
  }

  return (
    <Form {...studentForm}>
      <form
        onSubmit={studentForm.handleSubmit(onSubmit)}
        className="mx-auto max-w-3xl space-y-7 rounded-2xl px-7 py-10 shadow-[0px_0px_30px_rgba(0,44,122,0.13)] sm:px-10"
      >
        <div className="flex w-full flex-col gap-2 text-center">
          <div className="text-2xl font-bold lg:text-3xl">Welcome Student</div>
          <p className="text-base text-muted-foreground">
            Please enter the assignment key provided by your instructor
          </p>
        </div>
        <ToggleFormButton
          activeForm={activeForm}
          onSwitch={(value) => onSwitch(value)}
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
                  autoComplete="new-password"
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
          Submit
        </LoadingButton>
      </form>
    </Form>
  );
}
