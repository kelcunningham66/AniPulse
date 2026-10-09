import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { FollowButton } from "../components/FollowButton"
import { Mark } from "../components/Mark"
import { ErrorState, Loading } from "../components/States"
import { UpdateCard } from "../components/UpdateCard"
import { Button } from "../components/ui/button"
import { useFetch } from "../hooks"
import { api } from "../api"
import { kindLabel, percent } from "../lib/format"
import { useApp } from "../state"
import type { TitleDetail } from "../types"

const REGIONS = [
  { id: "US", label: "United States" },
  { id: "GB", label: "United Kingdom" },
  { id: "JP", label: "Japan" },
  { id: "CA", label: "Canada" },
]

export function TitlePage() {
  const { slug = "" } = useParams()
  const { me, patchMe, bump } = useApp()
  const [region, setRegion] = useState<string | null>(null)
  const [episode, setEpisode] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const chosen = region ?? me?.region ?? "US"
  const detail = useFetch<TitleDetail>(`/api/titles/${slug}?region=${chosen}`)

  useEffect(() => {
    setEpisode(null)
    setRegion(null)
  }, [slug])

  if (detail.loading && !detail.data) return <Loading label="Opening the title" />
  if (detail.error || !detail.data) return <ErrorState message={detail.error ?? "Unknown error"} onRetry={detail.reload} />

  const title = detail.data
  const progressValue = episode ?? String(title.progress)
  const confidence = percent(title.prediction.confidence)

  async function saveProgress() {
    setSaving(true)
    try {
      await api(`/api/titles/${slug}/progress`, {
        method: "PUT",
        body: JSON.stringify({ episode: Number(progressValue) || 0 }),
      })
      setEpisode(null)
      bump()
      detail.reload()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <header className="grid gap-4 md:grid-cols-[160px_1fr] md:items-end">
        <Mark name={title.name} accent={title.accent} className="h-44 rounded-2xl" />
        <div>
          <p className="kicker text-faint">
            {kindLabel(title.kind)} · {title.season_label} · {title.status}
          </p>
          <h1 className="mt-2 font-serif text-5xl leading-none sm:text-6xl">{title.name}</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-mist">{title.logline}</p>
          {title.upcoming.length ? (
            <ul className="mt-3 space-y-1 text-sm">
              {title.upcoming.map((item) => (
                <li key={`${item.kind}-${item.label}`}>
                  {item.label} · {item.day} · {item.time}
                  {item.platform ? ` · ${item.platform}` : ""}
                  <span className="text-faint"> · {kindLabel(item.kind)}</span>
                  {item.note ? <span className="text-warn"> · {item.note}</span> : null}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <FollowButton targetType="title" slug={title.slug} followed={title.followed} onChange={detail.reload} />
            {title.studio ? (
              <Link to={`/studio/${title.studio.slug}`} className="text-sm text-mist underline-offset-4 hover:underline">
                {title.studio.name}
              </Link>
            ) : null}
            {title.franchise ? (
              <Link to={`/franchise/${title.franchise.slug}`} className="text-sm text-mist underline-offset-4 hover:underline">
                {title.franchise.name}
              </Link>
            ) : null}
          </div>
        </div>
      </header>

      {me?.audio_mode === "dub" ? (
        <p className="mt-4 text-sm text-mist">
          Your list is set to the {me.audio_language === "es" ? "Spanish" : "English"} dub. The tracker below still shows every language.
        </p>
      ) : null}
      {title.warning ? <p className="mt-4 text-sm text-warn">{title.warning}</p> : null}

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        <section className="panel p-5">
          <p className="kicker text-faint">Sub and dub</p>
          {title.tracks.length === 0 ? (
            <p className="mt-3 text-sm text-mist">This release isn't split by language.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {title.tracks.map((track) => (
                <li key={track.language} className="flex items-baseline justify-between gap-3 border-b border-white/8 pb-3">
                  <div>
                    <p>{track.name}</p>
                    <p className="text-sm text-mist">
                      {track.latest_episode ? `Episode ${track.latest_episode}` : "No episode yet"}
                      {track.next_episode && track.next_day ? ` · Next ${track.next_episode} on ${track.next_day}` : ""}
                    </p>
                  </div>
                  {track.behind && track.behind > 0 ? (
                    <span className="text-sm text-warn">{track.behind} behind</span>
                  ) : track.language !== "ja" ? (
                    <span className="text-sm text-good">Caught up</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          <form
            className="mt-4"
            onSubmit={(event) => {
              event.preventDefault()
              void saveProgress()
            }}
          >
            <label className="text-sm text-mist" htmlFor="progress">
              My progress
            </label>
            <div className="mt-2 flex gap-2">
              <input
                id="progress"
                inputMode="numeric"
                value={progressValue}
                onChange={(event) => setEpisode(event.target.value)}
                className="w-28 rounded-xl border border-white/10 bg-ink px-3 py-2"
              />
              <Button type="submit" variant="outline" disabled={saving}>
                {saving ? "Saving" : "Save"}
              </Button>
            </div>
            <p className="mt-2 text-xs text-faint">
              {me?.spoiler_protection ? "Spoiler protection is on." : "Spoiler protection is off."} Episode {title.progress} is the cutoff.
            </p>
          </form>
        </section>

        <section className="panel p-5">
          <p className="kicker text-faint">Streaming</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {REGIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setRegion(item.id)}
                className={`rounded-full border px-3 py-1 text-xs ${chosen === item.id ? "border-pulse bg-pulse/15" : "border-white/10 text-mist"}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <ul className="mt-4 space-y-2">
            {title.streaming.offers.map((offer) => (
              <li key={offer.service} className="flex items-center justify-between gap-3 text-sm">
                <span>
                  {offer.service}
                  {offer.note ? <span className="block text-xs text-faint">{offer.note}</span> : null}
                </span>
                <span className={offer.available ? "text-good" : "text-faint"}>
                  {offer.available ? (offer.is_new ? "Available · new" : "Available") : "Not available"}
                </span>
              </li>
            ))}
          </ul>
          {me && chosen !== me.region ? (
            <Button className="mt-4" variant="outline" onClick={() => patchMe({ region: chosen as "US" | "GB" | "JP" | "CA" })}>
              Use {chosen} as my region
            </Button>
          ) : null}
        </section>
      </div>

      <section className="panel mt-4 p-5">
        <p className="kicker text-pulse">Official and estimate</p>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <div>
            <p className="kicker text-faint">Official {title.prediction.subject ? `· ${title.prediction.subject}` : ""}</p>
            <p className="mt-2 font-serif text-4xl leading-none">{title.prediction.official_text || "Not confirmed"}</p>
          </div>
          <div>
            <p className="kicker text-faint">AI estimated window</p>
            {title.prediction.skipped || !title.prediction.estimated_window ? (
              <p className="mt-2 text-sm leading-6 text-mist">No estimate. A dated release is already on the calendar.</p>
            ) : (
              <>
                <p className="mt-2 font-serif text-4xl leading-none">{title.prediction.estimated_window}</p>
                <p className="mt-2 text-sm text-mist">Prediction confidence {confidence}%</p>
              </>
            )}
          </div>
        </div>
        {title.prediction.factors.length ? (
          <ul className="mt-4 space-y-2 text-sm text-mist">
            {title.prediction.factors.map((factor) => (
              <li key={factor}>{factor}</li>
            ))}
          </ul>
        ) : null}
        <p className="mt-4 text-sm text-warn">{title.prediction.disclaimer}</p>
      </section>

      <section className="mt-8">
        <h2 className="font-serif text-3xl">Updates</h2>
        <div className="mt-4 grid gap-4">
          {title.updates.length === 0 ? (
            <p className="text-sm text-mist">No classified update for this title yet.</p>
          ) : (
            title.updates.map((item) => <UpdateCard key={item.id} item={item} />)
          )}
        </div>
      </section>
    </div>
  )
}
