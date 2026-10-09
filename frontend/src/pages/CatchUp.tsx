import { useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api"
import { Empty, ErrorState, Loading } from "../components/States"
import { Button } from "../components/ui/button"
import { useFetch } from "../hooks"
import { cn } from "../lib/utils"
import { useApp } from "../state"
import type { CatchGroup, Library } from "../types"

const WINDOWS = [
  { id: "last", label: "Since last visit" },
  { id: "7", label: "7 days" },
  { id: "30", label: "30 days" },
  { id: "60", label: "60 days" },
]

export function CatchUp() {
  const { refresh } = useApp()
  const [since, setSince] = useState("last")
  const [slug, setSlug] = useState("")
  const library = useFetch<Library>("/api/library")
  const path = `/api/catchup?since=${since}${slug ? `&slug=${slug}` : ""}`
  const report = useFetch<{ since: string; groups: CatchGroup[] }>(path)

  async function mark(pathName: string) {
    await api(pathName, { method: "POST" })
    await refresh()
  }

  if (report.loading && !report.data) return <Loading label="Catching you up" />
  if (report.error || !report.data) return <ErrorState message={report.error ?? "Unknown error"} onRetry={report.reload} />

  const titles = library.data?.title ?? []

  return (
    <div>
      <header className="mb-6">
        <p className="kicker text-pulse">What did I miss?</p>
        <h1 className="mt-2 font-serif text-5xl leading-none">Since you last checked.</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-mist">
          A short list of what actually changed. Story details past your progress stay out while spoiler protection is on.
        </p>
      </header>
      <div className="mb-4 flex flex-wrap gap-2">
        {WINDOWS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSince(item.id)}
            className={cn(
              "rounded-full border border-white/10 px-3 py-1 text-sm",
              since === item.id && "border-pulse bg-pulse/15",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      <label className="mb-6 block text-sm text-mist">
        Show
        <select
          value={slug}
          onChange={(event) => setSlug(event.target.value)}
          className="mt-1 block w-full max-w-sm rounded-xl border border-white/10 bg-panel px-3 py-2 text-cream"
        >
          <option value="">Everything you follow</option>
          {titles.map((title) => (
            <option key={title.slug} value={title.slug}>
              {title.name}
            </option>
          ))}
        </select>
      </label>

      {report.data.groups.length === 0 ? (
        <Empty title="You're caught up.">Nothing important landed in this window.</Empty>
      ) : (
        <div className="grid gap-4">
          {report.data.groups.map((group) => (
            <article key={`${group.kind}-${group.slug}`} className="panel p-5">
              <Link to={group.kind === "person" ? `/person/${group.slug}` : `/title/${group.slug}`} className="font-serif text-3xl">
                {group.name}
              </Link>
              <ul className="mt-4 space-y-2">
                {group.bullets.map((bullet) => (
                  <li key={bullet} className="flex gap-3 text-sm leading-6">
                    <span className="text-pulse">•</span>
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
              {group.hidden_note ? <p className="mt-3 text-sm text-warn">{group.hidden_note}</p> : null}
            </article>
          ))}
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => mark("/api/me/checked")}>
          I'm caught up
        </Button>
        <Button variant="ghost" onClick={() => mark("/api/me/rewind")}>
          I stepped away for two months
        </Button>
      </div>
    </div>
  )
}
