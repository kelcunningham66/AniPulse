import { Bell, CalendarDays, Compass, History, LayoutList, MessageCircle, Radar, Rss, Settings2 } from "lucide-react"
import { useState, type ReactNode } from "react"
import { NavLink } from "react-router-dom"
import { useApp } from "../state"
import { Dialog } from "./ui/dialog"
import { Switch } from "./ui/switch"
import { cn } from "../lib/utils"

const NAV = [
  { to: "/", label: "Watchlist", icon: LayoutList },
  { to: "/feed", label: "Feed", icon: Rss },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/ask", label: "Ask", icon: MessageCircle },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/catch-up", label: "Catch up", icon: History },
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/pulse", label: "Pulse lab", icon: Radar },
]

const REGIONS = [
  { id: "US", label: "United States" },
  { id: "GB", label: "United Kingdom" },
  { id: "JP", label: "Japan" },
  { id: "CA", label: "Canada" },
] as const

export function Shell({ children }: { children: ReactNode }) {
  const { me, patchMe, error } = useApp()
  const [open, setOpen] = useState(false)
  const dubValue = me?.audio_mode === "dub" ? me.audio_language : "all"

  return (
    <div className="min-h-svh md:pl-60">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-white/10 bg-ink/80 px-4 py-5 backdrop-blur md:flex">
        <Brand />
        <nav className="mt-8 grid gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-mist",
                  isActive && "bg-panel text-cream",
                )
              }
            >
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-3 text-xs text-faint">
          <p>For {me?.display_name ?? "you"}</p>
          <p>Conceived by Kel</p>
          <p>Built with Grok 4.7</p>
        </div>
      </aside>

      <div className="mx-auto w-full max-w-6xl px-4 pb-24 pt-4 md:px-8 md:pb-16 md:pt-8">
        <div className="mb-6 flex items-center justify-between md:justify-end">
          <div className="flex items-center gap-4 md:hidden">
            <Brand />
            <NavLink to="/pulse" className="text-sm text-mist">
              Lab
            </NavLink>
          </div>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-2 text-sm text-mist"
          >
            <Settings2 size={15} />
            Preferences
          </button>
        </div>
        {error ? <p className="mb-4 text-sm text-warn">Preferences didn't load. {error}</p> : null}
        {children}
        <footer className="mt-12 text-xs text-faint">
          Sample catalog for this build. Dates are demonstration data, not live network listings. Times are ET.
        </footer>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 flex overflow-x-auto border-t border-white/10 bg-ink/95 px-2 py-2 backdrop-blur md:hidden">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn("flex min-w-16 shrink-0 flex-col items-center gap-1 py-1 text-[10px] text-faint", isActive && "text-cream")
            }
          >
            <item.icon size={16} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Preferences"
        description="These change the watchlist, the calendar, and what the feed is allowed to say."
      >
        {me ? (
          <div className="space-y-5">
            <label className="flex items-center justify-between gap-4">
              <span>
                <span className="block text-sm">Spoiler protection</span>
                <span className="block text-xs text-faint">Hide story details past your progress.</span>
              </span>
              <Switch checked={me.spoiler_protection} onCheckedChange={(checked) => patchMe({ spoiler_protection: checked })} />
            </label>
            <label className="flex items-center justify-between gap-4">
              <span>
                <span className="block text-sm">Reminders</span>
                <span className="block text-xs text-faint">In-app, {me.notify_lead_minutes} minutes before a release.</span>
              </span>
              <Switch checked={me.notify_enabled} onCheckedChange={(checked) => patchMe({ notify_enabled: checked })} />
            </label>
            <div>
              <p className="text-sm">How early</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {[15, 30, 60, 120].map((minutes) => (
                  <button
                    key={minutes}
                    type="button"
                    onClick={() => patchMe({ notify_lead_minutes: minutes })}
                    className={cn(
                      "rounded-full border border-white/10 px-3 py-1 text-xs",
                      me.notify_lead_minutes === minutes && "border-pulse bg-pulse/15 text-cream",
                    )}
                  >
                    {minutes} min
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm">What you watch</p>
              <div className="mt-2 grid gap-2">
                {[
                  { id: "all", label: "Everything, including subs" },
                  { id: "en", label: "I only watch the English dub" },
                  { id: "es", label: "I only watch the Spanish dub" },
                ].map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() =>
                      patchMe(
                        option.id === "all"
                          ? { audio_mode: "all", audio_language: "en" }
                          : { audio_mode: "dub", audio_language: option.id as "en" | "es" },
                      )
                    }
                    className={cn(
                      "rounded-2xl border border-white/10 px-3 py-2 text-left text-sm",
                      dubValue === option.id && "border-pulse bg-pulse/10",
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm">Region</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {REGIONS.map((region) => (
                  <button
                    key={region.id}
                    type="button"
                    onClick={() => patchMe({ region: region.id })}
                    className={cn(
                      "rounded-full border border-white/10 px-3 py-1 text-xs",
                      me.region === region.id && "border-pulse bg-pulse/15",
                    )}
                  >
                    {region.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-mist">Preferences are still loading.</p>
        )}
      </Dialog>
    </div>
  )
}

function Brand() {
  return (
    <NavLink to="/" className="flex items-center gap-2">
      <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-pulse" />
      <span className="font-serif text-2xl tracking-tight">
        Ani<span className="italic text-pulse">Pulse</span>
      </span>
    </NavLink>
  )
}
