export function formatPosted(iso: string | null) {
  if (!iso) return ""
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "America/New_York",
  }).format(new Date(iso))
}

export function todayEt() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "numeric",
    day: "numeric",
  }).formatToParts(new Date())
  const pick = (type: string) => Number(parts.find((part) => part.type === type)?.value)
  return { year: pick("year"), month: pick("month"), day: pick("day") }
}

export function isoDate(year: number, month: number, day: number) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
}

export function addDays(year: number, month: number, day: number, amount: number) {
  const date = new Date(Date.UTC(year, month - 1, day + amount))
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1, day: date.getUTCDate() }
}

export function weekdayMonday(year: number, month: number, day: number) {
  const date = new Date(Date.UTC(year, month - 1, day))
  return (date.getUTCDay() + 6) % 7
}

export const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

export function percent(value: number | null) {
  if (value === null) return null
  return Math.round(value * 100)
}

export function kindLabel(kind: string) {
  const labels: Record<string, string> = {
    anime: "Anime",
    tv: "TV",
    movie: "Movie",
    manga: "Manga",
    person: "Actor",
    studio: "Studio",
    franchise: "Franchise",
    sub: "Sub",
    dub_en: "English dub",
    dub_es: "Spanish dub",
    premiere: "Premiere",
  }
  return labels[kind] ?? kind
}
