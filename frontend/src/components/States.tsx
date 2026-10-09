import type { ReactNode } from "react"
import { Button } from "./ui/button"

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="grid gap-3" aria-live="polite">
      <p className="text-sm text-mist">{label}</p>
      <div className="panel h-28 animate-pulse bg-panel-2" />
      <div className="panel h-28 animate-pulse bg-panel-2" />
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="panel border-pulse/40 p-6">
      <p className="font-serif text-2xl">AniPulse can't reach the service.</p>
      <p className="mt-2 text-sm text-mist">{message}. Start the API and try again.</p>
      {onRetry ? (
        <Button className="mt-4" onClick={onRetry} variant="outline">
          Retry
        </Button>
      ) : null}
    </div>
  )
}

export function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="panel p-6">
      <p className="font-serif text-3xl">{title}</p>
      <div className="mt-2 max-w-xl text-sm leading-6 text-mist">{children}</div>
    </div>
  )
}
