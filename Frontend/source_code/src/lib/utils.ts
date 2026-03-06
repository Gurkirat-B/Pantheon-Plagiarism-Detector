import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export async function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function formatDate(dateStr: string) {
  const [year, month, day] = dateStr.split("-");
  return `${parseInt(month)}/${parseInt(day)}/${year}`;
}
