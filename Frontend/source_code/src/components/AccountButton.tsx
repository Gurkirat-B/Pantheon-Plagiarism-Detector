"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { User, KeyRound, Trash2, ShieldCheck } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LoadingButton } from "@/components/LoadingButton";
import { PasswordInput } from "@/components/ui/password-input";
import { toast } from "@/hooks/use-toast";
import { changePasswordFormSchema } from "@/components/forms/formSchema";

// ─── Types ────────────────────────────────────────────────────────────────────

type DialogType = "password" | "delete" | null;

interface AccountButtonProps {
  name: string;
  email: string;
}

// ─── Change Password Dialog ───────────────────────────────────────────────────

type ChangePasswordValues = z.infer<typeof changePasswordFormSchema>;

function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordFormSchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const isSubmitting = form.formState.isSubmitting;

  const onSubmit = async (data: ChangePasswordValues) => {
    try {
      const res = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: data.currentPassword,
          new_password: data.newPassword,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        form.setError("root", {
          message: json.message ?? "Failed to change password.",
        });
        return;
      }
      onOpenChange(false);
      toast({
        title: "Password changed",
        description: "Your password has been updated successfully.",
      });
    } catch {
      form.setError("root", {
        message: "Something went wrong. Please try again.",
      });
    }
  };

  const handleClose = (val: boolean) => {
    if (!val) form.reset();
    onOpenChange(val);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mb-1 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100">
            <KeyRound className="h-4 w-4 text-slate-600" />
          </div>
          <DialogTitle className="text-lg">Change password</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Choose a strong password with at least 6 characters, including
            uppercase, lowercase, and a number.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-4 py-1"
          >
            <FormField
              control={form.control}
              name="currentPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Current password</FormLabel>
                  <FormControl>
                    <PasswordInput placeholder="••••••••" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="newPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New password</FormLabel>
                  <FormControl>
                    <PasswordInput placeholder="••••••••" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirmPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm new password</FormLabel>
                  <FormControl>
                    <PasswordInput placeholder="••••••••" {...field} />
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
            <DialogFooter className="gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleClose(false)}
              >
                Cancel
              </Button>
              <LoadingButton loading={isSubmitting} type="submit">
                Save password
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Delete Account Dialog ────────────────────────────────────────────────────

function DeleteAccountDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const CONFIRM_PHRASE = "delete my account";
  const [input, setInput] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = input === CONFIRM_PHRASE && password.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/delete-account", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.message ?? "Failed to delete account.");
        return;
      }
      onOpenChange(false);
      router.push("/");
      router.refresh();
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setInput("");
    setPassword("");
    setError("");
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-md">
        <AlertDialogHeader>
          <div className="mb-1 flex h-9 w-9 items-center justify-center rounded-full bg-red-50">
            <Trash2 className="h-4 w-4 text-destructive" />
          </div>
          <AlertDialogTitle className="text-lg">
            Delete account
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                This will{" "}
                <span className="font-medium text-slate-700">
                  permanently delete
                </span>{" "}
                your account, all your courses, and all associated submissions.
                This action{" "}
                <span className="font-medium text-slate-700">
                  cannot be undone.
                </span>
              </p>
              <div className="rounded-md border border-destructive/20 bg-red-50/60 px-3 py-2.5">
                <p className="text-xs font-medium text-destructive">
                  Type{" "}
                  <span className="select-none font-mono font-semibold">
                    {CONFIRM_PHRASE}
                  </span>{" "}
                  to confirm.
                </p>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-3">
          <Input
            placeholder={CONFIRM_PHRASE}
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <PasswordInput
            placeholder="Current password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <AlertDialogFooter className="gap-2">
          <AlertDialogCancel onClick={handleCancel}>Cancel</AlertDialogCancel>
          <LoadingButton
            loading={loading}
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            Delete account
          </LoadingButton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function AccountButton({ name, email }: AccountButtonProps) {
  const [activeDialog, setActiveDialog] = useState<DialogType>(null);

  const initials =
    (name ?? "")
      .split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "?";

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="flex h-9 items-center gap-2.5 border border-slate-200 bg-slate-50 text-sm font-medium text-slate-700 shadow-sm transition-all hover:bg-slate-100 hover:shadow-none"
          >
            {/* Avatar circle */}
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-[10px] font-semibold tracking-wide text-white">
              {initials}
            </span>
            Profile
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-64" sideOffset={8}>
          {/* User info header */}
          <div className="px-3 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-white">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-800">
                  {name || "Professor"}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {email || "—"}
                </p>
              </div>
            </div>
            <div className="mt-2.5 flex items-center gap-1.5 rounded-md bg-slate-50 px-2 py-1.5">
              <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              <span className="text-xs text-slate-500">Professor account</span>
            </div>
          </div>

          <DropdownMenuSeparator />

          {/* Account details submenu */}
          <DropdownMenuSub>
            <DropdownMenuSubTrigger className="gap-2 px-3 py-2 text-sm">
              <User className="h-4 w-4 text-slate-500" />
              Account details
            </DropdownMenuSubTrigger>
            <DropdownMenuPortal>
              <DropdownMenuSubContent className="w-52" sideOffset={6}>
                <DropdownMenuItem
                  className="gap-2 px-3 py-2 text-sm"
                  onClick={() => setActiveDialog("password")}
                >
                  <KeyRound className="h-4 w-4 text-slate-500" />
                  Change password
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="gap-2 px-3 py-2 text-sm text-destructive focus:text-destructive"
                  onClick={() => setActiveDialog("delete")}
                >
                  <Trash2 className="h-4 w-4" />
                  Delete account
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuPortal>
          </DropdownMenuSub>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Dialogs — mounted outside the dropdown so they survive its unmount */}
      <ChangePasswordDialog
        open={activeDialog === "password"}
        onOpenChange={(open) => !open && setActiveDialog(null)}
      />
      <DeleteAccountDialog
        open={activeDialog === "delete"}
        onOpenChange={(open) => !open && setActiveDialog(null)}
      />
    </>
  );
}
