import { Link } from "react-router-dom"
import { Mark } from "../components/Mark"
import { Empty, ErrorState, Loading } from "../components/States"
import { useFetch } from "../hooks"
import { kindLabel } from "../lib/format"
import { useApp } from "../state"
import type { Notifications, WatchCard } from "../types"

export function Dashboard() {
  const { me } = useApp()
  const list = useFetch<{ items: WatchCard[] }>("/api/watchlist")
  const reminders = useFetch<Notifications>("/api/notifications")

  if (list.loading) return <Loading label="Loading your watchlist" />
  if (list.error || !list.data) return <ErrorState message={list.error ?? "Unknown error"} onRetry={list.reload} />

  const next = reminders.data?.items[0]
  const warnings = list.data.items.filter((item) => item.warning)

  return (
    <div>
      <header className="mb-8 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
        <div>
          <p className="kicker text-pulse">My watchlist</p>
          <h1 className="mt-2 font-serif text-5xl leading-none sm:text-6xl">What matters this week.</h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-mist">
            {me?.audio_mode === "dub"
              ? `You're following the ${me.audio_language === "es" ? "Spanish" : "English"} dub. Sub releases stay off these cards.`
              : "Follow a show once. AniPulse keeps the next episode, the dub, and the platform in one place."}
          </p>
        </div>
        {next ? (
          <div className="panel w-full max-w-sm p-4">
            <p className="kicker text-faint">Next release</p>
            <p className="mt-2 font-serif text-3xl leading-none">
              {next.name} {next.label}
            </p>
            <p className="mt-2 text-sm text-mist">
              {next.day} · {next.time}
            </p>
            {reminders.data?.enabled ? (
              <p className="mt-3 text-sm text-good">Reminder {next.lead_minutes} minutes before · {next.fire_label}</p>
            ) : (
              <p className="mt-3 text-sm text-faint">Reminders are off.</p>
            )}
          </div>
        ) : null}
      </header>

      {warnings.length ? (
        <p className="mb-4 text-sm text-warn">
          {warnings.length === 1 ? "1 schedule changed." : `${warnings.length} schedules changed.`}{" "}
          {warnings.map((item) => item.name).join(", ")}.
        </p>
      ) : null}

      {list.data.items.length === 0 ? (
        <Empty title="Nothing followed yet.">
          The watchlist stays empty until you follow a show, a movie, or a manga. Discover is the place to add them.
        </Empty>
      ) : (
        <div className="grid gap-3">
          {list.data.items.map((item) => (
            <Link key={item.slug} to={`/title/${item.slug}`} className="panel group grid gap-4 p-4 sm:grid-cols-[104px_1fr]">
              <Mark name={item.name} accent={item.accent} className="h-28 rounded-xl sm:h-full sm:min-h-32" />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-xs text-faint">
                  <span className="kicker">{kindLabel(item.kind)}</span>
                  <span>{item.season_label}</span>
                </div>
                <h2 className="mt-1 font-serif text-4xl leading-none group-hover:text-white">{item.name}</h2>
                <p className="mt-3 text-lg">{item.primary}</p>
                <ul className="mt-2 space-y-1 text-sm text-mist">
                  {item.lines.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
                {item.warning ? (
                  <p className="mt-3 inline-flex rounded-full bg-warn/15 px-3 py-1 text-sm text-warn">{item.warning}</p>
                ) : null}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
