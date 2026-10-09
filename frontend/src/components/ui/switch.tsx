import * as SwitchPrimitive from "@radix-ui/react-switch"
import { cn } from "../../lib/utils"

export function Switch({ className, ...props }: SwitchPrimitive.SwitchProps) {
  return (
    <SwitchPrimitive.Root
      className={cn(
        "relative h-7 w-12 shrink-0 rounded-full bg-white/15 transition data-[state=checked]:bg-pulse",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb className="block h-5 w-5 translate-x-1 rounded-full bg-cream transition data-[state=checked]:translate-x-6" />
    </SwitchPrimitive.Root>
  )
}
