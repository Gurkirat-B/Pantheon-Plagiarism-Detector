"use client";

import { CheckCircle2, File as FileIcon, Trash } from "lucide-react";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import JSZip from "jszip";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { cn } from "@/lib/utils";
import { LoadingButton } from "./LoadingButton";

const MAX_FILE_SIZE = 50 * 1024 * 1024;

const formSchema = z.object({
  files: z
    .array(z.instanceof(File))
    .min(1, "Please upload a file.")
    .refine(
      (files) => files.every((f) => f.name.endsWith(".zip")),
      "Only .zip files are accepted.",
    )
    .refine(
      (files) => files.every((f) => f.size <= MAX_FILE_SIZE),
      "File must be 50MB or less.",
    ),
});

type FormValues = z.infer<typeof formSchema>;

export function FileUploadDialog({
  open,
  onClose,
  title,
  description,
  onUpload,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description: string;
  onUpload: (file: File) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { files: [] },
  });

  const watchedFiles = form.watch("files");

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "application/zip": [".zip"] },
    maxFiles: 1,
    onDrop: async (acceptedFiles) => {
      const file = acceptedFiles[0];
      if (!file) return;

      try {
        const zip = await JSZip.loadAsync(file);
        const fileNames = Object.keys(zip.files).filter(
          (name) => !zip.files[name].dir,
        );
        const hasValidSource = fileNames.some((name) =>
          [".java", ".cpp", ".c"].some((ext) => name.endsWith(ext)),
        );
        if (!hasValidSource) {
          form.setError("files", {
            type: "manual",
            message:
              "The zip must contain at least one .java, .cpp, or .c file.",
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

      form.clearErrors("files");
      form.setValue("files", [file], { shouldValidate: true });
    },
  });

  const handleClose = () => {
    form.reset();
    setSuccess(false);
    onClose();
  };

  const onSubmit = async (data: FormValues) => {
    setLoading(true);
    try {
      await onUpload(data.files[0]);
      form.reset();
      setSuccess(true);
    } catch (err) {
      form.setError("root", {
        type: "manual",
        message:
          err instanceof Error ? err.message : "Upload failed. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        {success ? (
          <div className="flex flex-col items-center gap-5 py-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50">
              <CheckCircle2 className="h-9 w-9 text-emerald-600" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-xl font-bold">Upload Successful!</h2>
              <p className="text-sm text-muted-foreground">
                Your file has been uploaded successfully.
              </p>
            </div>
            <Button className="w-full" onClick={handleClose}>
              Done
            </Button>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <p className="text-sm text-muted-foreground">{description}</p>

              <FormField
                control={form.control}
                name="files"
                render={() => (
                  <FormItem>
                    <FormLabel className="font-medium">Zip file</FormLabel>
                    <FormControl>
                      <div
                        {...getRootProps()}
                        className={cn(
                          isDragActive
                            ? "border-primary bg-primary/10 ring-2 ring-primary/20"
                            : "border-border",
                          "mt-2 flex cursor-pointer justify-center rounded-md border border-dashed px-6 py-12 transition-colors duration-200",
                        )}
                      >
                        <div className="text-center">
                          <FileIcon
                            className="mx-auto h-10 w-10 text-muted-foreground/80"
                            aria-hidden
                          />
                          <div className="mt-3 flex text-sm text-muted-foreground">
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
                    <p className="mt-1 flex justify-between text-xs text-muted-foreground">
                      <span>Only .zip files are accepted.</span>
                      <span>Max. 50MB</span>
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {watchedFiles.length > 0 && (
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted">
                      <FileIcon className="h-4 w-4 text-foreground" />
                    </span>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {watchedFiles[0].name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {(watchedFiles[0].size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => form.setValue("files", [])}
                  >
                    <Trash className="h-4 w-4" />
                  </Button>
                </div>
              )}

              {form.formState.errors.root && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.root.message}
                </p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <LoadingButton loading={loading} type="submit">
                  Upload
                </LoadingButton>
              </div>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
