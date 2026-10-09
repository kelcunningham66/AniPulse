import { useState } from "react"
import { UpdateCard } from "../components/UpdateCard"
import { Empty, ErrorState, Loading } from "../components/States"
import { useFetch } from "../hooks"
import { cn } from "../lib/utils"
import type { FeedResponse } from "../types"

const FILTERS = [
  { id: "all", label: "All" },
  { id: "schedule", label: "Schedule" },
  { id: "streaming", label: "Streaming" },
  { id: "production", label: "Production" },
  { id: "dub", label: "Dubs" },
]

function matches(type: string, filter: string) {
  if (filter === "all") return true
  if (filter === "production") return ["production", "premiere", "trailer", "visual", "manga"].includes(type)
  if (filter === "dub") return type === "dub" || type === "cast"
  return type === filter
}

export function Feed() {
  const { data, error, loading, reload } = useFetch<FeedResponse>("/api/feed")
  const [filter, setFilter] = useState("all")

  if (loading) return <Loading label="Reading your feed" />
  if (error || !data) return <ErrorState message={error ?? "Unknown error"} onRetry={reload} />

  const updates = data.updates.filter((item) => matches(item.primary_type, filter))

  return (
    <div>
      <header className="mb-6">
        <p className="kicker text-pulse">Personal feed</p>
        <h1 className="mt-2 font-serif text-5xl leading-none">One update, not six articles.</h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-mist">
          {data.stats.collected} items collected. {data.stats.discarded} discarded as fan noise or empty posts.{" "}
          {data.stats.pending} still waiting in Pulse lab.
        </p>
      </header>
      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-pressed={filter === item.id}
            onClick={() => setFilter(item.id)}
            className={cn(
              "rounded-full border border-white/10 px-3 py-1 text-sm text-mist",
              filter === item.id && "border-pulse bg-pulse/15 text-cream",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      {updates.length === 0 ? (
        <Empty title="Nothing in this filter.">
          Fan edits, tier lists, and meetup photos are left out on purpose. Scan Pulse lab if a source is still waiting.
        </Empty>
      ) : (
        <div className="grid gap-4">
          {updates.map((item) => (
            <UpdateCard key={item.id} item={item} />
          ))}
        </div>
      )}
      {data.public.length ? (
        <section className="mt-10">
          <h2 className="font-serif text-3xl">From public sources</h2>
          <p className="mt-2 text-sm text-mist">These matched a pull, not a show you follow.</p>
          <div className="mt-4 grid gap-4">
            {data.public.map((item) => (
              <UpdateCard key={item.id} item={item} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
