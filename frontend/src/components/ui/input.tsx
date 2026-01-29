import { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-fog bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-ink focus:outline-none",
        className
      )}
      {...props}
    />
  );
}