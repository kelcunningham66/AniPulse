export type Me = {
  display_name: string
  region: string
  audio_mode: "all" | "dub"
  audio_language: "en" | "es" | "ja"
  spoiler_protection: boolean
  notify_enabled: boolean
  notify_lead_minutes: number
  last_checked_at: string | null
}

export type WatchCard = {
  slug: string
  name: string
  kind: string
  season_label: string
  status: string
  accent: string
  logline: string
  primary: string
  lines: string[]
  warning: string | null
  next_at: string | null
}

export type UpdateItem = {
  id: number
  slug: string | null
  name: string
  headline: string
  kicker: string
  changes: string[]
  hidden_count: number
  hidden_note: string | null
  confidence: number
  confidence_label: string
  sources_verified: number
  sources: { publisher: string; medium: string }[]
  published_at: string | null
  is_new: boolean
  primary_type: string
  accent: string
  person_slug: string | null
  person_name: string | null
}

export type FeedResponse = {
  updates: UpdateItem[]
  public: UpdateItem[]
  stats: { collected: number; published: number; discarded: number; pending: number }
}

export type ReleaseItem = {
  id: number
  slug: string
  name: string
  accent: string
  label: string
  kind: string
  starts_at: string
  day: string
  time: string
  platform: string | null
  note: string | null
}

export type NotificationItem = {
  id: number
  slug: string
  name: string
  label: string
  kind: string
  starts_at: string
  day: string
  time: string
  fire_at: string
  fire_label: string
  lead_minutes: number
}

export type Notifications = {
  enabled: boolean
  lead_minutes: number
  items: NotificationItem[]
  channels: { in_app: boolean; email: boolean; push: boolean; note: string }
}

export type Track = {
  language: string
  name: string
  latest_episode: number | null
  next_episode: number | null
  next_at: string | null
  next_day: string | null
  behind: number | null
}

export type Offer = {
  service: string
  available: boolean
  is_new: boolean
  note: string
}

export type Prediction = {
  subject: string
  official_text: string
  estimated_window: string | null
  confidence: number | null
  factors: string[]
  disclaimer: string
  skipped: boolean
}

export type TitleDetail = {
  slug: string
  name: string
  kind: string
  season_label: string
  status: string
  logline: string
  genres: string[]
  accent: string
  followed: boolean
  progress: number
  warning: string | null
  upcoming: { label: string; kind: string; day: string; time: string; platform: string | null; note: string | null }[]
  tracks: Track[]
  streaming: { region: string; offers: Offer[] }
  prediction: Prediction
  updates: UpdateItem[]
  studio: { slug: string; name: string; blurb: string } | null
  franchise: { slug: string; name: string; blurb: string } | null
}

export type CatchGroup = {
  slug: string
  name: string
  accent: string
  kind: string
  bullets: string[]
  hidden_count: number
  hidden_note: string | null
}

export type Recommendation = {
  slug: string
  name: string
  kind: string
  season_label: string
  logline: string
  accent: string
  genres: string[]
  match: number
  reason: string
  themes: string[]
}

export type SearchHit = {
  target_type: "title" | "person" | "studio" | "franchise"
  slug: string
  name: string
  detail: string
  kind: string
  accent: string
  followed: boolean
}

export type Library = {
  title: { slug: string; name: string; detail: string; accent: string }[]
  person: { slug: string; name: string; detail: string; accent: string }[]
  studio: { slug: string; name: string; detail: string; accent: string }[]
  franchise: { slug: string; name: string; detail: string; accent: string }[]
}

export type Entity = {
  kind: string
  profile: { slug: string; name: string; blurb: string; accent: string; role: string }
  followed: boolean
  titles: { slug: string; name: string; season_label: string; accent: string; kind: string }[]
  updates: UpdateItem[]
}

export type ClassifyResult = {
  signal_probability: number
  noise_probability: number
  predicted_type: string
  type_probability: number
  meaningful: boolean
  kicker: string
  changes: string[]
  spoiler: boolean
}

export type ScanResult = {
  updates: { headline: string; kicker: string; changes: string[]; confidence_label: string; sources_verified: number }[]
  discarded: { headline: string; reason: string }[]
  fetched?: number
  errors?: string[]
}
