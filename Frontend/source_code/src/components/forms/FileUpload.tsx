"use client";

import { File as FileIcon, Trash } from "lucide-react";
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
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { Separator } from "@/components/ui/separator";
import { cn, delay } from "@/lib/utils";
import { LoadingButton } from "../LoadingButton";

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

const formSchema = z.object({
  files: z
    .array(z.instanceof(File))
    .min(1, "Please upload at least one file.")
    .refine(
      (files) => files.every((file) => file.size <= MAX_FILE_SIZE),
      "Each file must be 50MB or less.",
    ),
});

type FormValues = z.infer<typeof formSchema>;

export default function FileUpload() {
  const [loading, setLoading] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { files: [] },
  });

  const watchedFiles = form.watch("files");

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
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
    await delay(3000);
    console.log("Submitted files:", data.files);
    setLoading(false);
    // handle upload logic here
  };

  return (
    <div className="flex items-center justify-center p-10">
      <Card className="sm:mx-auto sm:min-w-[450px]">
        <CardHeader>
          <CardTitle>Assignment Name - Course</CardTitle>
          <CardDescription>
            Please consider to pack everything into one zip file
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
                    <FormLabel className="font-medium">
                      {"File(s) upload"}
                    </FormLabel>
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
                              {"choose file(s)"}
                            </span>
                            <input {...getInputProps()} />
                            <p className="pl-1">to upload</p>
                          </div>
                        </div>
                      </div>
                    </FormControl>
                    <p className="mt-2 text-sm leading-5 text-muted-foreground sm:flex sm:items-center sm:justify-between">
                      <span>All file types are allowed.</span>
                      <span>Max. size per file: 50MB</span>
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {watchedFiles.length > 0 && (
                <>
                  <h4 className="mt-6 font-medium text-foreground">
                    File(s) to upload
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

              <Separator className="my-6" />
              <div className="flex items-center justify-end space-x-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => form.reset()}
                >
                  Cancel
                </Button>
                <LoadingButton loading={loading} type="submit">
                  Submit
                </LoadingButton>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
