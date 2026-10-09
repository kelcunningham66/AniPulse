import { cn } from "../lib/utils"

export function Mark({ name, accent, className }: { name: string; accent: string; className?: string }) {
  const initials = name
    .split(/\s+/)
    .filter((part) => part[0] && part[0] === part[0].toUpperCase())
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
  return (
    <div className={cn("relative overflow-hidden", className)} style={{ backgroundColor: accent }} aria-hidden>
      <div className="absolute inset-0 bg-gradient-to-br from-white/25 via-transparent to-ink/70" />
      <div className="absolute -right-5 -top-8 h-24 w-24 rounded-full border border-white/35" />
      <div className="absolute bottom-4 left-5 h-px w-10 bg-white/70" />
      <span className="absolute bottom-5 left-5 font-serif text-2xl text-white">{initials || "AP"}</span>
    </div>
  )
}
