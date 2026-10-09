import { Link } from "react-router-dom"
import { formatPosted, percent } from "../lib/format"
import type { UpdateItem } from "../types"

export function UpdateCard({ item }: { item: UpdateItem }) {
  const confidence = percent(item.confidence) ?? 0
  return (
    <article className="panel relative overflow-hidden p-5">
      <div className="absolute inset-y-0 left-0 w-1" style={{ background: item.accent }} />
      <div className="flex flex-wrap items-center gap-3 pl-2">
        <p className="kicker text-pulse">{item.is_new ? "New update" : "Update"}</p>
        <p className="text-xs text-faint">{formatPosted(item.published_at)}</p>
        {item.slug ? (
          <Link to={`/title/${item.slug}`} className="text-xs text-mist underline-offset-4 hover:underline">
            {item.name}
          </Link>
        ) : (
          <span className="text-xs text-mist">{item.name}</span>
        )}
      </div>
      <h2 className="mt-3 pl-2 font-serif text-4xl leading-none">{item.headline}</h2>
      <p className="mt-3 pl-2 text-mist">{item.kicker}</p>
      <div className="mt-5 pl-2">
        <p className="kicker text-faint">What changed</p>
        {item.changes.length ? (
          <ul className="mt-3 space-y-2">
            {item.changes.map((change) => (
              <li key={change} className="flex gap-3 text-sm leading-6">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-pulse" />
                <span>{change}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-mist">The facts in this item are hidden.</p>
        )}
        {item.hidden_note ? <p className="mt-3 text-sm text-warn">{item.hidden_note}</p> : null}
      </div>
      <div className="mt-6 grid gap-4 border-t border-white/10 pt-4 pl-2 sm:grid-cols-2">
        <div>
          <p className="kicker text-faint">Confidence · {item.confidence_label}</p>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-good" style={{ width: `${confidence}%` }} />
          </div>
        </div>
        <div>
          <p className="kicker text-faint">Sources verified · {item.sources_verified}</p>
          <ul className="mt-2 space-y-1 text-sm text-mist">
            {item.sources.map((source) => (
              <li key={source.publisher}>
                {source.publisher}
                <span className="text-faint"> · {source.medium}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  )
}
