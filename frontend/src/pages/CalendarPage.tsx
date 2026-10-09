import { ChevronLeft, ChevronRight } from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorState, Loading } from "../components/States"
import { useFetch } from "../hooks"
import { addDays, isoDate, kindLabel, MONTHS, todayEt, WEEKDAYS, weekdayMonday } from "../lib/format"
import { cn } from "../lib/utils"
import { useApp } from "../state"
import type { Notifications, ReleaseItem } from "../types"

const FILTERS = [
  { id: "sub", label: "Sub releases", kinds: ["sub"] },
  { id: "dub", label: "Dub releases", kinds: ["dub_en", "dub_es"] },
  { id: "movie", label: "Movies", kinds: ["movie"] },
  { id: "premiere", label: "Season premieres", kinds: ["premiere"] },
  { id: "manga", label: "Manga chapters", kinds: ["manga"] },
]

export function CalendarPage() {
  const { me } = useApp()
  const initial = todayEt()
  const [cursor, setCursor] = useState({ year: initial.year, month: initial.month })
  const [selected, setSelected] = useState(isoDate(initial.year, initial.month, initial.day))
  const [active, setActive] = useState<string[]>(FILTERS.map((item) => item.id))

  const grid = useMemo(() => buildGrid(cursor.year, cursor.month), [cursor])
  const kinds = FILTERS.filter((item) => active.includes(item.id)).flatMap((item) => item.kinds)
  const allOn = active.length === FILTERS.length
  const query = new URLSearchParams({ start: grid[0].iso, end: grid[grid.length - 1].iso })
  if (!allOn) query.set("kinds", kinds.length ? kinds.join(",") : "none")

  const calendar = useFetch<{ releases: ReleaseItem[] }>(`/api/calendar?${query.toString()}`)
  const reminders = useFetch<Notifications>("/api/notifications")

  if (calendar.loading && !calendar.data) return <Loading label="Building the calendar" />
  if (calendar.error || !calendar.data) return <ErrorState message={calendar.error ?? "Unknown error"} onRetry={calendar.reload} />

  const byDay = new Map<string, ReleaseItem[]>()
  for (const release of calendar.data.releases) {
    const list = byDay.get(release.day) ?? []
    list.push(release)
    byDay.set(release.day, list)
  }
  const selectedReleases = byDay.get(selected) ?? []
  const today = isoDate(initial.year, initial.month, initial.day)

  function shift(amount: number) {
    const date = new Date(Date.UTC(cursor.year, cursor.month - 1 + amount, 1))
    const year = date.getUTCFullYear()
    const month = date.getUTCMonth() + 1
    setCursor({ year, month })
    setSelected(isoDate(year, month, 1))
  }

  function toggle(id: string) {
    setActive((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="kicker text-pulse">Release calendar</p>
          <h1 className="mt-2 font-serif text-5xl leading-none">
            {MONTHS[cursor.month - 1]} {cursor.year}
          </h1>
        </div>
        <div className="flex gap-2">
          <button type="button" className="rounded-full border border-white/10 p-2" onClick={() => shift(-1)} aria-label="Previous month">
            <ChevronLeft size={18} />
          </button>
          <button type="button" className="rounded-full border border-white/10 p-2" onClick={() => shift(1)} aria-label="Next month">
            <ChevronRight size={18} />
          </button>
        </div>
      </header>

      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-pressed={active.includes(item.id)}
            onClick={() => toggle(item.id)}
            className={cn(
              "rounded-full border border-white/10 px-3 py-1 text-sm text-mist",
              active.includes(item.id) && "border-pulse bg-pulse/15 text-cream",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {me?.audio_mode === "dub" ? (
        <p className="mb-4 text-sm text-mist">
          Dub-only is on, so sub dates are hidden here too. Switch preferences if you want the Japanese schedule back.
        </p>
      ) : null}

      {reminders.data?.items.length ? (
        <div className="panel mb-4 p-4">
          <p className="kicker text-faint">Reminders</p>
          <ul className="mt-3 space-y-2 text-sm">
            {reminders.data.items.slice(0, 4).map((item) => (
              <li key={item.id} className="flex flex-wrap justify-between gap-2">
                <span>
                  {item.name} {item.label}
                  <span className="text-mist"> · {item.day} {item.time}</span>
                </span>
                <span className="text-good">{item.lead_minutes} min before · {item.fire_label}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-faint">{reminders.data.channels.note}</p>
        </div>
      ) : null}

      <div className="hidden md:block">
        <div className="grid grid-cols-7 gap-2 text-center text-xs text-faint">
          {WEEKDAYS.map((day) => (
            <div key={day} className="py-1">
              {day}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-2">
          {grid.map((cell) => {
            const releases = byDay.get(cell.iso) ?? []
            const inMonth = cell.month === cursor.month
            return (
              <button
                key={cell.iso}
                type="button"
                onClick={() => setSelected(cell.iso)}
                className={cn(
                  "min-h-28 rounded-2xl border border-white/8 p-2 text-left",
                  inMonth ? "bg-panel" : "bg-transparent opacity-40",
                  cell.iso === selected && "border-pulse",
                  cell.iso === today && "ring-1 ring-white/30",
                )}
              >
                <span className="text-xs text-mist">{cell.day}</span>
                <div className="mt-2 space-y-1">
                  {releases.slice(0, 3).map((release) => (
                    <p key={release.id} className="truncate text-[11px] leading-4">
                      <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full" style={{ background: release.accent }} />
                      {release.name} {release.label}
                    </p>
                  ))}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      <section className="mt-6">
        <h2 className="font-serif text-3xl">{prettyDay(selected)}</h2>
        {selectedReleases.length === 0 ? (
          <p className="mt-2 text-sm text-mist">Nothing on this day for the filters you have on.</p>
        ) : (
          <ul className="mt-3 grid gap-2">
            {selectedReleases.map((release) => (
              <li key={release.id}>
                <Link to={`/title/${release.slug}`} className="panel flex items-center justify-between gap-3 px-4 py-3">
                  <span>
                    <span className="block">{release.name}</span>
                    <span className="text-sm text-mist">
                      {release.label} · {kindLabel(release.kind)} · {release.time}
                      {release.platform ? ` · ${release.platform}` : ""}
                    </span>
                  </span>
                  {release.note ? <span className="text-sm text-warn">{release.note}</span> : null}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-8 md:hidden">
        <h2 className="font-serif text-3xl">This month</h2>
        <div className="mt-3 space-y-4">
          {[...byDay.entries()].map(([day, releases]) => (
            <div key={day}>
              <p className="text-xs text-faint">{day}</p>
              <ul className="mt-1 space-y-2">
                {releases.map((release) => (
                  <li key={release.id}>
                    <Link to={`/title/${release.slug}`} className="block text-sm">
                      {release.name} {release.label}
                      <span className="text-mist"> · {release.time}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function prettyDay(iso: string) {
  const [year, month, day] = iso.split("-").map(Number)
  return `${MONTHS[month - 1]} ${day}, ${year}`
}

function buildGrid(year: number, month: number) {
  const offset = weekdayMonday(year, month, 1)
  const start = addDays(year, month, 1, -offset)
  return Array.from({ length: 42 }, (_, index) => {
    const date = addDays(start.year, start.month, start.day, index)
    return { ...date, iso: isoDate(date.year, date.month, date.day) }
  })
}
