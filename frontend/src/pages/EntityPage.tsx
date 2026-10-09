import { Link, useParams } from "react-router-dom"
import { FollowButton } from "../components/FollowButton"
import { ErrorState, Loading } from "../components/States"
import { UpdateCard } from "../components/UpdateCard"
import { useFetch } from "../hooks"
import { kindLabel } from "../lib/format"
import type { Entity } from "../types"

export function EntityPage({ kind }: { kind: "studio" | "person" | "franchise" }) {
  const { slug = "" } = useParams()
  const detail = useFetch<Entity>(`/api/entities/${kind}/${slug}`)

  if (detail.loading && !detail.data) return <Loading label="Opening the page" />
  if (detail.error || !detail.data) return <ErrorState message={detail.error ?? "Unknown error"} onRetry={detail.reload} />

  const entity = detail.data
  return (
    <div>
      <p className="kicker text-faint">{entity.profile.role}</p>
      <h1 className="mt-2 font-serif text-5xl leading-none">{entity.profile.name}</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-mist">{entity.profile.blurb}</p>
      <div className="mt-4">
        <FollowButton
          targetType={kind}
          slug={entity.profile.slug}
          followed={entity.followed}
          onChange={detail.reload}
        />
      </div>
      <section className="mt-8">
        <h2 className="font-serif text-3xl">Related titles</h2>
        <ul className="mt-3 grid gap-2">
          {entity.titles.map((title) => (
            <li key={title.slug}>
              <Link to={`/title/${title.slug}`} className="panel block px-4 py-3">
                {title.name}
                <span className="text-sm text-mist">
                  {" "}
                  · {kindLabel(title.kind)} · {title.season_label}
                </span>
              </Link>
            </li>
          ))}
          {entity.titles.length === 0 ? <li className="text-sm text-mist">No related titles in this catalog.</li> : null}
        </ul>
      </section>
      <section className="mt-8 grid gap-4">
        {entity.updates.map((item) => (
          <UpdateCard key={item.id} item={item} />
        ))}
      </section>
    </div>
  )
}
