import { useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api"
import { Empty, ErrorState, Loading } from "../components/States"
import { Button } from "../components/ui/button"
import { Switch } from "../components/ui/switch"
import { useFetch } from "../hooks"
import { useApp } from "../state"
import type { Notifications } from "../types"

type AlertPref = "notify_episodes" | "notify_dubs" | "notify_delays" | "notify_renewals" | "notify_streaming"

const TYPES: { key: AlertPref; id: string; label: string; detail: string }[] = [
  { key: "notify_episodes", id: "episode", label: "New episodes", detail: "Subs, movies, premieres, and chapters." },
  { key: "notify_dubs", id: "dub", label: "Dubbed releases", detail: "English and Spanish dubs you follow." },
  { key: "notify_delays", id: "delay", label: "Delays", detail: "A date moved or a week was skipped." },
  { key: "notify_renewals", id: "renewal", label: "Renewals", detail: "A new season was actually announced." },
  { key: "notify_streaming", id: "streaming", label: "New streaming", detail: "A service added a show in your region." },
]

const DELIVERY: Record<string, string> = {
  sent: "Sent",
  recorded: "Held here",
  failed: "Failed",
  skipped: "Skipped",
}

export function Alerts() {
  const { me, patchMe } = useApp()
  const inbox = useFetch<Notifications>("/api/notifications")
  const [email, setEmail] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  if (inbox.loading && !inbox.data) return <Loading label="Checking alerts" />
  if (inbox.error || !inbox.data) return <ErrorState message={inbox.error ?? "Unknown error"} onRetry={inbox.reload} />

  const alerts = inbox.data.alerts
  const address = email ?? me?.email_address ?? ""
  const device = token ?? me?.push_token ?? ""

  async function saveDestinations() {
    setSaving(true)
    try {
      await patchMe({ email_address: address.trim(), push_token: device.trim() })
      setEmail(null)
      setToken(null)
    } finally {
      setSaving(false)
    }
  }

  async function markRead(id?: number) {
    await api("/api/notifications/read", { method: "POST", body: JSON.stringify({ id: id ?? null }) })
    inbox.reload()
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="kicker text-pulse">Alerts</p>
          <h1 className="mt-2 font-serif text-5xl leading-none">Once per story.</h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-mist">{inbox.data.channels.note}</p>
        </div>
        {inbox.data.unread ? (
          <Button variant="outline" onClick={() => markRead()}>
            Mark {inbox.data.unread} read
          </Button>
        ) : null}
      </header>

      {me ? (
        <section className="panel mb-4 grid gap-5 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Toggle
              label="In-app"
              detail="The list on this page."
              checked={me.notify_in_app}
              onChange={(checked) => patchMe({ notify_in_app: checked })}
            />
            <Toggle
              label="Email"
              detail={inbox.data.channels.smtp_configured ? "SMTP is configured." : "Held here until SMTP is set."}
              checked={me.notify_email}
              onChange={(checked) => patchMe({ notify_email: checked })}
            />
            <Toggle
              label="Push"
              detail={inbox.data.channels.push_configured ? "Firebase is configured." : "Held here until FCM is set."}
              checked={me.notify_push}
              onChange={(checked) => patchMe({ notify_push: checked })}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              Email address
              <input
                value={address}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                className="mt-1 w-full rounded-xl border border-white/10 bg-ink px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm">
              Push device token
              <input
                value={device}
                onChange={(event) => setToken(event.target.value)}
                placeholder="Firebase token"
                className="mt-1 w-full rounded-xl border border-white/10 bg-ink px-3 py-2 text-sm"
              />
            </label>
          </div>
          <div>
            <Button variant="outline" disabled={saving} onClick={saveDestinations}>
              {saving ? "Saving" : "Save address and token"}
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {TYPES.map((item) => (
              <Toggle
                key={item.id}
                label={item.label}
                detail={item.detail}
                checked={Boolean(me[item.key])}
                onChange={(checked) => patchMe({ [item.key]: checked })}
              />
            ))}
          </div>
        </section>
      ) : null}

      {alerts.length === 0 ? (
        <Empty title="No alerts for the types you have on.">
          Followed shows with a new episode, dub, delay, renewal, or streaming add land here. A story that already sent stays sent.
        </Empty>
      ) : (
        <div className="grid gap-3">
          {alerts.map((alert) => (
            <article key={alert.id} className="panel p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="kicker text-faint">{alert.category}</p>
                {alert.read ? <span className="text-xs text-faint">Read</span> : <span className="text-xs text-pulse">New</span>}
              </div>
              <h2 className="mt-2 font-serif text-3xl leading-none">
                {alert.slug ? <Link to={`/title/${alert.slug}`}>{alert.headline}</Link> : alert.headline}
              </h2>
              <p className="mt-3 text-sm leading-6 text-mist">{alert.body}</p>
              <ul className="mt-3 flex flex-wrap gap-2">
                {alert.deliveries.map((delivery) => (
                  <li key={delivery.channel} className="rounded-full border border-white/10 px-3 py-1 text-xs text-mist">
                    {delivery.channel === "in_app" ? "In-app" : delivery.channel === "email" ? "Email" : "Push"} · {DELIVERY[delivery.status] ?? delivery.status}
                  </li>
                ))}
              </ul>
              {alert.deliveries[0]?.detail ? <p className="mt-2 text-xs text-faint">{alert.deliveries.map((item) => item.detail).filter(Boolean)[0]}</p> : null}
              {!alert.read ? (
                <button type="button" className="mt-3 text-xs text-mist underline" onClick={() => markRead(alert.id)}>
                  Mark read
                </button>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

function Toggle({
  label,
  detail,
  checked,
  onChange,
}: {
  label: string
  detail: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 px-3 py-3">
      <span>
        <span className="block text-sm">{label}</span>
        <span className="block text-xs text-faint">{detail}</span>
      </span>
      <Switch checked={checked} onCheckedChange={onChange} />
    </label>
  )
}
