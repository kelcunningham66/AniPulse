import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api"
import { FollowButton } from "../components/FollowButton"
import { Mark } from "../components/Mark"
import { Empty, ErrorState, Loading } from "../components/States"
import { useFetch } from "../hooks"
import { kindLabel } from "../lib/format"
import { useApp } from "../state"
import type { Library, Recommendation, SearchHit } from "../types"

export function Discover() {
  const { version } = useApp()
  const recs = useFetch<{ items: Recommendation[] }>("/api/recommendations")
  const library = useFetch<Library>("/api/library")
  const [query, setQuery] = useState("")
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const trimmed = query.trim()
      if (!trimmed) {
        setHits(null)
        setSearchError(null)
        return
      }
      api<{ items: SearchHit[] }>(`/api/search?q=${encodeURIComponent(trimmed)}`)
        .then((result) => {
          setHits(result.items)
          setSearchError(null)
        })
        .catch((reason: Error) => setSearchError(reason.message))
    }, 250)
    return () => window.clearTimeout(handle)
  }, [query, version])

  if (recs.loading && !recs.data) return <Loading label="Finding matches" />
  if (recs.error || !recs.data) return <ErrorState message={recs.error ?? "Unknown error"} onRetry={recs.reload} />

  return (
    <div>
      <header className="mb-6">
        <p className="kicker text-pulse">Watchlist intelligence</p>
        <h1 className="mt-2 font-serif text-5xl leading-none">Because of what you follow.</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-mist">
          Matches come from the themes on your list. The percentage is cosine similarity, and the sentence names the shows that pulled it up.
        </p>
      </header>

      <label className="mb-8 block">
        <span className="kicker text-faint">Search shows, people, studios, franchises</span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try MAPPA, Aleks Le, or Kaiju"
          className="mt-2 w-full rounded-2xl border border-white/10 bg-panel px-4 py-3 text-cream outline-none placeholder:text-faint"
        />
      </label>

      {searchError ? <p className="mb-4 text-sm text-warn">{searchError}</p> : null}
      {hits && hits.length === 0 ? (
        <p className="mb-6 text-sm text-mist">No people, studios, or titles match that.</p>
      ) : null}
      {hits && hits.length > 0 ? (
        <ul className="mb-8 grid gap-2">
          {hits.map((hit) => (
            <li key={`${hit.target_type}-${hit.slug}`} className="panel flex items-center justify-between gap-3 px-4 py-3">
              <Link to={hrefFor(hit.target_type, hit.slug)}>
                <span className="block">{hit.name}</span>
                <span className="text-xs text-faint">
                  {kindLabel(hit.kind)} · {hit.detail}
                </span>
              </Link>
              <FollowButton targetType={hit.target_type} slug={hit.slug} followed={hit.followed} />
            </li>
          ))}
        </ul>
      ) : null}

      {recs.data.items.length === 0 ? (
        <Empty title="Follow a few shows first.">Recommendations need a list to compare against.</Empty>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {recs.data.items.map((item) => (
            <article key={item.slug} className="panel overflow-hidden">
              <div className="grid sm:grid-cols-[120px_1fr]">
                <Mark name={item.name} accent={item.accent} className="min-h-36" />
                <div className="p-4">
                  <p className="font-serif text-5xl leading-none tabular-nums">{item.match}%</p>
                  <p className="kicker mt-1 text-faint">match</p>
                  <h2 className="mt-3 font-serif text-3xl leading-none">
                    <Link to={`/title/${item.slug}`}>{item.name}</Link>
                  </h2>
                  <p className="mt-1 text-xs text-faint">
                    {kindLabel(item.kind)} · {item.season_label}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-mist">{item.reason}</p>
                  <p className="mt-2 text-sm">{item.logline}</p>
                  <div className="mt-4">
                    <FollowButton targetType="title" slug={item.slug} followed={false} onChange={recs.reload} />
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <section className="mt-10">
        <h2 className="font-serif text-3xl">Already on your pulse</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <FollowGroup title="Studios" items={library.data?.studio ?? []} kind="studio" />
          <FollowGroup title="People" items={library.data?.person ?? []} kind="person" />
          <FollowGroup title="Franchises" items={library.data?.franchise ?? []} kind="franchise" />
        </div>
      </section>
    </div>
  )
}

function FollowGroup({
  title,
  items,
  kind,
}: {
  title: string
  items: { slug: string; name: string; detail: string }[]
  kind: "studio" | "person" | "franchise"
}) {
  if (!items.length) return null
  return (
    <div className="panel p-4">
      <p className="kicker text-faint">{title}</p>
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item.slug}>
            <Link to={`/${kind}/${item.slug}`} className="text-sm">
              {item.name}
              <span className="text-faint"> · {item.detail}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

function hrefFor(type: SearchHit["target_type"], slug: string) {
  if (type === "title") return `/title/${slug}`
  return `/${type}/${slug}`
}
