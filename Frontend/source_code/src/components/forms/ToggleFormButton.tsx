"use client";

import { CircleUserRound, GraduationCap } from "lucide-react";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";

type FormState = "student" | "instructor";

interface ToggleFormButtonProps {
  activeForm: FormState;
  onSwitch: (value: FormState) => void;
}

export default function ToggleFormButton({
  activeForm,
  onSwitch,
}: ToggleFormButtonProps) {
  return (
    <ToggleGroup
      type="single"
      value={activeForm}
      onValueChange={(value) => {
        if (value) onSwitch(value as FormState);
      }}
      className="m-auto gap-1 rounded-lg bg-muted p-1"
    >
      <ToggleGroupItem
        value="student"
        className="flex items-center gap-2 !rounded-lg !px-5 py-2 text-sm font-medium text-muted-foreground transition-all hover:text-foreground data-[state=on]:bg-white data-[state=on]:text-foreground data-[state=on]:shadow-sm"
      >
        <GraduationCap className="h-4 w-4" />
        Student
      </ToggleGroupItem>
      <ToggleGroupItem
        value="instructor"
        className="flex items-center gap-2 !rounded-lg !px-5 py-2 text-sm font-medium text-muted-foreground transition-all hover:text-foreground data-[state=on]:bg-white data-[state=on]:text-foreground data-[state=on]:shadow-sm"
      >
        <CircleUserRound className="h-4 w-4" />
        Instructor
      </ToggleGroupItem>
    </ToggleGroup>
  );
}
