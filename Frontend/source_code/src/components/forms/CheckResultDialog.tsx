"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import { ShieldCheck, Clock } from "lucide-react";

// ─── Schema ───────────────────────────────────────────────────────────────────

const schema = z.object({
  submission_id: z.string().trim().min(1, "Please enter your submission ID."),
});

type FormValues = z.infer<typeof schema>;

// ─── Score color helper ───────────────────────────────────────────────────────

function getScoreColor(score: number) {
  if (score >= 60) return "text-red-500";
  if (score >= 30) return "text-orange-400";
  return "text-emerald-500";
}

function getScoreLabel(score: number) {
  if (score >= 85) return "Critical";
  if (score >= 60) return "High";
  if (score >= 40) return "Medium";
  return "Low";
}

function getScoreBg(score: number) {
  if (score >= 60) return "bg-red-50 border-red-200";
  if (score >= 30) return "bg-orange-50 border-orange-200";
  return "bg-emerald-50 border-emerald-200";
}

// ─── Result dialogs ───────────────────────────────────────────────────────────

function ScoreResultDialog({
  open,
  onClose,
  score,
}: {
  open: boolean;
  onClose: () => void;
  score: number;
}) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-xl">Similarity Result</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col items-center gap-5 py-4 text-center">
          <div
            className={`flex h-20 w-20 items-center justify-center rounded-full border-2 ${getScoreBg(score)}`}
          >
            <ShieldCheck className={`h-10 w-10 ${getScoreColor(score)}`} />
          </div>
          <div>
            <p
              className={`text-5xl font-bold tabular-nums ${getScoreColor(score)}`}
            >
              {score}%
            </p>
            <p className={`mt-1 text-sm font-medium ${getScoreColor(score)}`}>
              {getScoreLabel(score)} Similarity
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function PendingResultDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-xl">Not Available Yet</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col items-center gap-5 py-4 text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full border-2 border-slate-200 bg-slate-50">
            <Clock className="h-10 w-10 text-slate-400" />
          </div>
          <div>
            <p className="text-lg font-semibold text-slate-800">
              Analysis Pending
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Your submission has been received but the similarity analysis
              hasn&apos;t been completed yet. Please check back later.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function CheckResultDialog() {
  const [lookupOpen, setLookupOpen] = useState(false);
  const [scoreOpen, setScoreOpen] = useState(false);
  const [pendingOpen, setPendingOpen] = useState(false);
  const [score, setScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { submission_id: "" },
  });

  const onSubmit = async (data: FormValues) => {
    setLoading(true);
    try {
      //   const res = await fetch("/api/submissions/result", {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({ submission_id: data.submission_id }),
      //   });

      //   const result = await res.json();

      //   if (!res.ok) {
      //     form.setError("submission_id", {
      //       type: "manual",
      //       message: result.message ?? "Submission not found.",
      //     });
      //     return;
      //   }
      // Close lookup dialog before opening result
      setLookupOpen(false);
      form.reset();
      // if (result.similarity_score === result.similarity_score) {
      //   setScore(result.similarity_score);
      //   setScoreOpen(true);
      // } else {
      //   setPendingOpen(true);
      // }
      setPendingOpen(true);
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
      {/* Trigger */}
      <Dialog
        open={lookupOpen}
        onOpenChange={(val) => {
          setLookupOpen(val);
          if (!val) form.reset();
        }}
      >
        <DialogTrigger asChild>
          <span className="cursor-pointer font-medium underline transition-opacity hover:opacity-70">
            Click here
          </span>
        </DialogTrigger>

        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-xl">Check Your Result</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Enter the submission ID you received after submitting your
            assignment.
          </p>

          <Form {...form}>
            <form
              onSubmit={(e) => {
                e.stopPropagation();
                form.handleSubmit(onSubmit)(e);
              }}
              className="space-y-4 pt-1"
            >
              <FormField
                control={form.control}
                name="submission_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Submission ID</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g. xxxxxxxx-xxxx-xxxx-xxxx..."
                        autoComplete="off"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {form.formState.errors.root && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.root.message}
                </p>
              )}

              <LoadingButton
                loading={loading}
                type="button"
                className="w-full"
                onClick={(e) => {
                  e.stopPropagation();
                  form.handleSubmit(onSubmit)();
                }}
              >
                Check Result
              </LoadingButton>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Score result dialog */}
      {score != null && (
        <ScoreResultDialog
          open={scoreOpen}
          onClose={() => setScoreOpen(false)}
          score={score}
        />
      )}

      {/* Pending result dialog */}
      <PendingResultDialog
        open={pendingOpen}
        onClose={() => setPendingOpen(false)}
      />
    </>
  );
}
