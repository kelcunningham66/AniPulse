import * as DialogPrimitive from "@radix-ui/react-dialog"
import type { ReactNode } from "react"

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/70" />
        <DialogPrimitive.Content className="panel fixed left-1/2 top-1/2 z-50 max-h-[min(720px,calc(100%-2rem))] w-[min(480px,calc(100%-1.5rem))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto p-5 shadow-2xl">
          <DialogPrimitive.Title className="font-serif text-3xl">{title}</DialogPrimitive.Title>
          {description ? <DialogPrimitive.Description className="mt-2 text-sm text-mist">{description}</DialogPrimitive.Description> : null}
          <div className="mt-5">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
