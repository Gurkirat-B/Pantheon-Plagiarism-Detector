"use client";
import { useState } from "react";
import StudentForm from "./StudentForm";
import LoginForm from "./LoginForm";

type FormState = "student" | "instructor";
export default function MainForm() {
  const [formState, setFormState] = useState<FormState>("student");

  return (
    <div className="relative w-full max-w-lg flex-shrink-0 lg:max-w-xl lg:basis-1/2">
      {formState === "student" ? <StudentForm activeForm={formState} onSwitch={(value) => setFormState(value)}/> : <LoginForm activeForm={formState} onSwitch={(value) => setFormState(value)}/>}
    </div>
  );
}
