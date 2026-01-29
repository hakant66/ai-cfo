import { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
}

export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "rounded-md px-4 py-2 text-sm font-semibold transition",
        variant === "primary" && "bg-ink text-white hover:bg-dusk",
        variant === "ghost" && "bg-transparent text-ink hover:bg-fog",
        variant === "danger" && "bg-crimson text-white hover:bg-red-600",
        className
      )}
      {...props}
    />
  );
}