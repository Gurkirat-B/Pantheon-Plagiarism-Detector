"use client";

import { CheckCircle2, File as FileIcon, Trash } from "lucide-react";
import React, { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { LoadingButton } from "../LoadingButton";
import JSZip from "jszip";

const SOURCE_EXTENSIONS = [".java", ".cpp", ".c"];

async function zipHasValidSource(zip: JSZip, depth = 0): Promise<boolean> {
  if (depth > 3) return false;
  for (const [name, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue;
    if (SOURCE_EXTENSIONS.some((ext) => name.endsWith(ext))) return true;
    if (name.endsWith(".zip")) {
      try {
        const buf = await entry.async("arraybuffer");
        const nested = await JSZip.loadAsync(buf);
        if (await zipHasValidSource(nested, depth + 1)) return true;
      } catch {
        // skip unreadable nested zip
      }
    }
  }
  return false;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

const formSchema = z.object({
  files: z
    .array(z.instanceof(File))
    .min(1, "Please upload at least one file.")
    .refine(
      (files) => files.every((file) => file.name.endsWith(".zip")),
      "Only .zip files are accepted.",
    )
    .refine(
      (files) => files.every((file) => file.size <= MAX_FILE_SIZE),
      "Each file must be 50MB or less.",
    ),
});

type FormValues = z.infer<typeof formSchema>;

export default function FileUpload() {
  const [loading, setLoading] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { files: [] },
  });

  const watchedFiles = form.watch("files");

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "application/zip": [".zip"] },
    onDrop: async (acceptedFiles) => {
      for (const file of acceptedFiles) {
        try {
          const zip = await JSZip.loadAsync(file);
          const hasValidSource = await zipHasValidSource(zip);
          if (!hasValidSource) {
            form.setError("files", {
              type: "manual",
              message:
                "The zip must contain at least one .java, .cpp, or .c file (including inside nested zips).",
            });
            return;
          }
        } catch {
          form.setError("files", {
            type: "manual",
            message: "Could not read the zip file. Please try again.",
          });
          return;
        }
      }

      // All files passed — clear any previous error and set value
      form.clearErrors("files");
      const current = form.getValues("files");
      form.setValue("files", [...current, ...acceptedFiles], {
        shouldValidate: true,
      });
    },
  });

  const removeFile = (fileName: string) => {
    const current = form.getValues("files");
    form.setValue(
      "files",
      current.filter((f) => f.name !== fileName),
    );
  };

  const onSubmit = async (data: FormValues) => {
    setLoading(true);
    try {
      const assignmentKey = sessionStorage.getItem("assignmentKey");
      if (!assignmentKey) {
        form.setError("root", {
          type: "manual",
          message: "Assignment key not found. Please log in again.",
        });
        return;
      }

      const body = new FormData();
      body.append("file", data.files[0]);

      const res = await fetch(`/api/submissions/${assignmentKey}`, {
        method: "POST",
        body,
      });
      const result = await res.json();

      if (!res.ok) {
        form.setError("root", {
          type: "manual",
          message: result.message ?? "Submission failed. Please try again.",
        });
        return;
      }

      form.reset();
      setSuccessOpen(true);
    } catch {
      form.setError("root", {
        type: "manual",
        message: "Something went wrong. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex items-center justify-center p-10">
        <Card className="sm:mx-auto sm:min-w-[450px]">
          <CardHeader>
            <CardTitle>Assignment Name - Course</CardTitle>
            <CardDescription>
              Please pack everything into one zip file before uploading
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)}>
                <FormField
                  control={form.control}
                  name="files"
                  render={() => (
                    <FormItem>
                      <FormLabel className="font-medium">File upload</FormLabel>
                      <FormControl>
                        <div
                          {...getRootProps()}
                          className={cn(
                            isDragActive
                              ? "border-primary bg-primary/10 ring-2 ring-primary/20"
                              : "border-border",
                            "mt-2 flex cursor-pointer justify-center rounded-md border border-dashed px-6 py-20 transition-colors duration-200",
                          )}
                        >
                          <div>
                            <FileIcon
                              className="mx-auto h-12 w-12 text-muted-foreground/80"
                              aria-hidden={true}
                            />
                            <div className="mt-4 flex text-muted-foreground">
                              <p>Drag and drop or</p>
                              <span className="relative pl-1 font-medium text-primary hover:text-primary/80 hover:underline hover:underline-offset-4">
                                choose a file
                              </span>
                              <input {...getInputProps()} />
                              <p className="pl-1">to upload</p>
                            </div>
                          </div>
                        </div>
                      </FormControl>
                      <p className="mt-2 text-sm leading-5 text-muted-foreground sm:flex sm:items-center sm:justify-between">
                        <span>Only .zip files are accepted.</span>
                        <span>Max. size: 50MB</span>
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {watchedFiles.length > 0 && (
                  <>
                    <h4 className="mt-6 font-medium text-foreground">
                      File to upload
                    </h4>
                    <ul role="list" className="mt-4 space-y-4">
                      {watchedFiles.map((file) => (
                        <li key={file.name}>
                          <Card className="relative p-4">
                            <div className="absolute right-4 top-1/2 -translate-y-1/2">
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                aria-label="Remove file"
                                onClick={() => removeFile(file.name)}
                              >
                                <Trash className="h-5 w-5" />
                              </Button>
                            </div>
                            <CardContent className="flex items-center space-x-3 p-0">
                              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted">
                                <FileIcon className="h-5 w-5 text-foreground" />
                              </span>
                              <div>
                                <p className="font-medium text-foreground">
                                  {file.name}
                                </p>
                                <p className="mt-0.5 text-sm text-muted-foreground">
                                  {(file.size / 1024).toFixed(1)} KB
                                </p>
                              </div>
                            </CardContent>
                          </Card>
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                {form.formState.errors.root && (
                  <p className="mt-4 text-sm text-destructive">
                    {form.formState.errors.root.message}
                  </p>
                )}

                <Separator className="my-6" />
                <div className="flex items-center justify-end space-x-3">
                  <LoadingButton loading={loading} type="submit">
                    Submit
                  </LoadingButton>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>

      <AlertDialog open={successOpen}>
        <AlertDialogContent className="sm:max-w-sm">
          <AlertDialogTitle className="sr-only">
            Submission Successful
          </AlertDialogTitle>
          <div className="flex flex-col items-center gap-5 py-2 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <CheckCircle2 className="h-9 w-9 text-primary" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-2xl font-bold">Submission Successful!</h2>
              <p className="text-base text-muted-foreground">
                Your assignment has been submitted successfully.
              </p>
            </div>
            <AlertDialogAction
              className="w-full"
              onClick={async () => {
                await fetch("/api/auth/logout", {
                  method: "POST",
                });
                sessionStorage.clear();
                window.location.href = "/";
              }}
            >
              Done
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
