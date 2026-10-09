import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import type { ButtonHTMLAttributes } from "react"
import { cn } from "../../lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full font-medium transition disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        default: "bg-pulse text-cream hover:brightness-110",
        outline: "border border-white/15 bg-transparent text-cream hover:bg-white/5",
        ghost: "bg-transparent text-cream hover:bg-white/5",
        good: "bg-good text-ink hover:brightness-105",
      },
      size: {
        default: "h-10 px-4 text-sm",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-5 text-base",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
)

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }

export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button"
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
