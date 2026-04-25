"use client";

import { useState } from "react";
import { ArrowLeft, MessageSquare, Send } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const MAX_MESSAGE_LENGTH = 1000;

export default function CustomerSupportPage() {
  const [message, setMessage] = useState("");

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-6 pt-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-5 py-2.5 text-sm font-medium text-foreground shadow-sm transition-all duration-200 hover:bg-muted hover:shadow-none"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>
      </div>

      <section className="mx-auto max-w-2xl px-6 pb-8 pt-10 text-center">
        <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-muted shadow-sm">
          <MessageSquare className="h-5 w-5 text-foreground" strokeWidth={1.5} />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Contact Support
        </h1>
        <p className="mx-auto mt-4 max-w-sm text-base leading-relaxed text-muted-foreground">
          Reach out to us — we&apos;re here to help with any issues or questions
          you have.
        </p>
        <div className="mx-auto mt-8 flex items-center justify-center gap-3">
          <div className="h-px w-12 bg-border" />
          <div className="h-1.5 w-1.5 rounded-full bg-[#d40f0d]" />
          <div className="h-px w-12 bg-border" />
        </div>
      </section>

      <section className="mx-auto max-w-2xl px-6 pb-24">
        <div className="rounded-2xl border border-border bg-card p-8 shadow-sm">
          <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-2">
              <Label
                htmlFor="email"
                className="text-sm font-semibold text-foreground"
              >
                Your Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="subject"
                className="text-sm font-semibold text-foreground"
              >
                Subject
              </Label>
              <Input
                id="subject"
                type="text"
                placeholder="Brief description of your issue"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="message"
                  className="text-sm font-semibold text-foreground"
                >
                  Message
                </Label>
                <span
                  className={`text-xs tabular-nums transition-colors ${
                    message.length >= MAX_MESSAGE_LENGTH
                      ? "text-destructive"
                      : "text-muted-foreground"
                  }`}
                >
                  {message.length} / {MAX_MESSAGE_LENGTH}
                </span>
              </div>
              <Textarea
                id="message"
                placeholder="Describe your issue or question in detail..."
                className="min-h-[160px] resize-none"
                maxLength={MAX_MESSAGE_LENGTH}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
            </div>

            <Button type="submit" className="w-full gap-2 py-6 text-base">
              <Send className="h-4 w-4" />
              Send Message
            </Button>
          </form>
        </div>

        <div className="mt-8 rounded-xl border border-border bg-muted/40 px-8 py-6 text-center">
          <p className="text-sm text-muted-foreground">
            You can also reach us directly at{" "}
            <a
              href="mailto:support@pantheon.dev"
              className="font-semibold text-foreground underline underline-offset-2 transition-colors hover:text-[#d40f0d]"
            >
              support@pantheon.dev
            </a>
            .
          </p>
        </div>
      </section>
    </main>
  );
}
