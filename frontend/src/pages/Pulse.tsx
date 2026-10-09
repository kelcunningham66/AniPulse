import { useState } from "react"
import { api } from "../api"
import { ErrorState, Loading } from "../components/States"
import { Button } from "../components/ui/button"
import { useFetch } from "../hooks"
import { percent } from "../lib/format"
import type { ClassifyResult, FeedResponse, ScanResult } from "../types"

export function Pulse() {
  const stats = useFetch<FeedResponse>("/api/feed")
  const [text, setText] = useState(
    "Official site: the new season trailer is out, with a Spring 2027 premiere window. Crunchyroll confirmed it will stream it.",
  )
  const [result, setResult] = useState<ClassifyResult | null>(null)
  const [scan, setScan] = useState<ScanResult | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function classify() {
    setBusy("classify")
    setError(null)
    try {
      setResult(await api<ClassifyResult>("/api/pulse/classify", { method: "POST", body: JSON.stringify({ text }) }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Classify failed")
    } finally {
      setBusy(null)
    }
  }

  async function run(path: string) {
    setBusy(path)
    setError(null)
    try {
      const next = await api<ScanResult>(path, { method: "POST" })
      setScan(next)
      stats.reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scan failed")
    } finally {
      setBusy(null)
    }
  }

  if (stats.loading && !stats.data) return <Loading label="Checking the queue" />
  if (stats.error || !stats.data) return <ErrorState message={stats.error ?? "Unknown error"} onRetry={stats.reload} />

  return (
    <div>
      <header className="mb-6">
        <p className="kicker text-pulse">Pulse lab</p>
        <h1 className="mt-2 font-serif text-5xl leading-none">Is this a real update?</h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-mist">
          A note comes in from an official site, a streamer, a studio, a news desk, social, or an episode database.
          The classifier scores it. The extractor lists what changed. Fan edits never reach the feed.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <label className="block text-sm" htmlFor="note">
            Paste an announcement
          </label>
          <textarea
            id="note"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={7}
            className="mt-2 w-full resize-y rounded-2xl border border-white/10 bg-ink px-3 py-3 text-sm leading-6"
          />
          <Button className="mt-3" onClick={classify} disabled={busy !== null || !text.trim()}>
            {busy === "classify" ? "Scoring" : "Score this note"}
          </Button>
          {result ? (
            <div className="mt-4 border-t border-white/10 pt-4 text-sm">
              <p className="font-serif text-2xl">{result.meaningful ? result.kicker : "Left out of the feed."}</p>
              <p className="mt-2 text-mist">
                Signal {percent(result.signal_probability)}% · noise {percent(result.noise_probability)}% · model type{" "}
                {result.predicted_type}
              </p>
              {result.changes.length ? (
                <ul className="mt-3 space-y-1">
                  {result.changes.map((change) => (
                    <li key={change}>• {change}</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-mist">No release, schedule, or availability fact to publish.</p>
              )}
              {result.spoiler ? <p className="mt-2 text-warn">This note looks like it contains story details.</p> : null}
            </div>
          ) : null}
        </section>

        <section className="panel p-4">
          <p className="kicker text-faint">Collection queue</p>
          <p className="mt-2 font-serif text-4xl">{stats.data.stats.pending} waiting</p>
          <p className="mt-2 text-sm text-mist">
            {stats.data.stats.discarded} items have already been rejected. Scanning writes a real schedule change onto the watchlist.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={() => run("/api/pulse/scan")} disabled={busy !== null}>
              {busy === "/api/pulse/scan" ? "Scanning" : "Scan waiting sources"}
            </Button>
            <Button variant="outline" onClick={() => run("/api/pulse/pull")} disabled={busy !== null}>
              {busy === "/api/pulse/pull" ? "Pulling" : "Pull public sources"}
            </Button>
          </div>
          {error ? <p className="mt-3 text-sm text-warn">{error}</p> : null}
          {scan?.errors?.length ? (
            <ul className="mt-3 text-sm text-warn">
              {scan.errors.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          {scan ? (
            <div className="mt-4 space-y-3 text-sm">
              {typeof scan.fetched === "number" ? <p className="text-mist">{scan.fetched} new public items stored.</p> : null}
              {scan.updates.map((item) => (
                <div key={item.headline} className="rounded-xl bg-white/5 p-3">
                  <p className="text-good">{item.confidence_label} · {item.kicker}</p>
                  <p className="mt-1">{item.headline}</p>
                  <ul className="mt-1 text-mist">
                    {item.changes.map((change) => (
                      <li key={change}>• {change}</li>
                    ))}
                  </ul>
                </div>
              ))}
              {scan.discarded.map((item) => (
                <div key={item.headline} className="rounded-xl bg-white/5 p-3">
                  <p className="text-faint">Discarded · {item.headline}</p>
                  <p className="text-mist">{item.reason}</p>
                </div>
              ))}
              {scan.updates.length === 0 && scan.discarded.length === 0 ? (
                <p className="text-mist">Nothing was waiting. Pull public sources if you want a live pass.</p>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  )
}
