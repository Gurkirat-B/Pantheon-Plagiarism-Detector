"use client";

import { useState } from "react";
import {
  User,
  Mail,
  KeyRound,
  Trash2,
  ShieldCheck,
} from "lucide-react";

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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingButton } from "@/components/LoadingButton";

// ─── Types ────────────────────────────────────────────────────────────────────

type DialogType = "email" | "password" | "delete" | null;

interface AccountButtonProps {
  name: string;
  email: string;
}

// ─── Shared field wrapper ─────────────────────────────────────────────────────

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm font-medium text-slate-700">{label}</Label>
      {children}
    </div>
  );
}

// ─── Change Email Dialog ──────────────────────────────────────────────────────

function ChangeEmailDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [newEmail, setNewEmail] = useState("");
  const [confirmEmail, setConfirmEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const mismatch = confirmEmail.length > 0 && newEmail !== confirmEmail;
  const canSubmit = newEmail.length > 0 && newEmail === confirmEmail;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    // TODO: wire to API
    await new Promise((r) => setTimeout(r, 800));
    console.log("Change email submitted:", { newEmail });
    setLoading(false);
    onOpenChange(false);
  };

  const handleCancel = () => {
    setNewEmail("");
    setConfirmEmail("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mb-1 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100">
            <Mail className="h-4 w-4 text-slate-600" />
          </div>
          <DialogTitle className="text-lg">Change email address</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Your new email will be used for sign-in and notifications.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <Field label="New email address">
            <Input
              type="email"
              placeholder="you@example.com"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
            />
          </Field>
          <Field label="Confirm new email">
            <Input
              type="email"
              placeholder="you@example.com"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              className={
                mismatch
                  ? "border-destructive focus-visible:ring-destructive"
                  : ""
              }
            />
            {mismatch && (
              <p className="text-xs text-destructive">
                Email addresses do not match.
              </p>
            )}
          </Field>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <LoadingButton
            loading={loading}
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            Save email
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Change Password Dialog ───────────────────────────────────────────────────

function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const mismatch = confirm.length > 0 && next !== confirm;
  const canSubmit = current.length > 0 && next.length >= 8 && next === confirm;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    // TODO: wire to API
    await new Promise((r) => setTimeout(r, 800));
    console.log("Change password submitted");
    setLoading(false);
    onOpenChange(false);
  };

  const handleCancel = () => {
    setCurrent("");
    setNext("");
    setConfirm("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mb-1 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100">
            <KeyRound className="h-4 w-4 text-slate-600" />
          </div>
          <DialogTitle className="text-lg">Change password</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Choose a strong password with at least 8 characters.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <Field label="Current password">
            <Input
              type="password"
              placeholder="••••••••"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </Field>
          <Field label="New password">
            <Input
              type="password"
              placeholder="••••••••"
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
            {next.length > 0 && next.length < 8 && (
              <p className="text-xs text-muted-foreground">
                At least 8 characters required.
              </p>
            )}
          </Field>
          <Field label="Confirm new password">
            <Input
              type="password"
              placeholder="••••••••"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={
                mismatch
                  ? "border-destructive focus-visible:ring-destructive"
                  : ""
              }
            />
            {mismatch && (
              <p className="text-xs text-destructive">
                Passwords do not match.
              </p>
            )}
          </Field>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <LoadingButton
            loading={loading}
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            Save password
          </LoadingButton>
        </DialogFooter>
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
  const CONFIRM_PHRASE = "delete my account";
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit = input === CONFIRM_PHRASE;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    // TODO: wire to API
    await new Promise((r) => setTimeout(r, 800));
    console.log("Delete account confirmed");
    setLoading(false);
    onOpenChange(false);
  };

  const handleCancel = () => {
    setInput("");
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

        <Input
          placeholder={CONFIRM_PHRASE}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="mt-1"
        />

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

  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

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
                  {name}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {email}
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
                  onClick={() => setActiveDialog("email")}
                >
                  <Mail className="h-4 w-4 text-slate-500" />
                  Change email
                </DropdownMenuItem>
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
      <ChangeEmailDialog
        open={activeDialog === "email"}
        onOpenChange={(open) => !open && setActiveDialog(null)}
      />
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
