import { useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api"
import { Button } from "../components/ui/button"
import type { AskAnswer } from "../types"

const PROMPTS = [
  "Did Solo Leveling get renewed?",
  "What's dropping this weekend?",
  "Which of my shows have new English dubs?",
  "What have I missed in the past month?",
]

export function Ask() {
  const [question, setQuestion] = useState("")
  const [turns, setTurns] = useState<AskAnswer[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setError(null)
    setQuestion("")
    try {
      const answer = await api<AskAnswer>("/api/ask", { method: "POST", body: JSON.stringify({ question: trimmed }) })
      setTurns((current) => [answer, ...current])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ask failed")
      setQuestion(trimmed)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <header className="mb-6">
        <p className="kicker text-pulse">Ask AniPulse</p>
        <h1 className="mt-2 font-serif text-5xl leading-none">Saved updates first.</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-mist">
          Questions are answered from the watchlist you follow. Every claim cites a saved update or a dated release. If a date was never announced, the answer says so.
        </p>
      </header>

      <form
        className="panel mb-4 flex flex-col gap-3 p-4 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault()
          void submit(question)
        }}
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about a show you follow"
          className="w-full rounded-xl border border-white/10 bg-ink px-3 py-2 text-sm"
        />
        <Button type="submit" disabled={busy || !question.trim()}>
          {busy ? "Looking" : "Ask"}
        </Button>
      </form>

      <div className="mb-6 flex flex-wrap gap-2">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => void submit(prompt)}
            className="rounded-full border border-white/10 px-3 py-1 text-left text-xs text-mist"
          >
            {prompt}
          </button>
        ))}
      </div>

      {error ? <p className="mb-4 text-sm text-warn">{error}</p> : null}
      {turns.length === 0 ? (
        <p className="text-sm leading-6 text-mist">
          Nothing asked yet. A renewal, a weekend, a dub, or a month of missed updates all read the same saved records.
        </p>
      ) : null}

      <div className="grid gap-3">
        {turns.map((turn) => (
          <article key={`${turn.question}-${turn.answer.slice(0, 24)}`} className="panel p-4">
            <p className="text-sm text-faint">{turn.question}</p>
            <p className="mt-3 text-base leading-7">{turn.answer}</p>
            {turn.unannounced ? (
              <p className="mt-3 text-sm text-warn">This is not filled in from a guess. The saved record does not announce it.</p>
            ) : null}
            {turn.citations.length ? (
              <ul className="mt-4 space-y-2">
                {turn.citations.map((citation) => (
                  <li key={`${citation.publisher}-${citation.headline}-${citation.slug}`} className="text-sm text-mist">
                    {citation.slug ? (
                      <Link to={`/title/${citation.slug}`} className="text-cream">
                        {citation.name}
                      </Link>
                    ) : (
                      citation.name
                    )}
                    {" · "}
                    {citation.publisher}: {citation.headline}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-xs text-faint">No saved source to cite.</p>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}
