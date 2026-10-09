import { useEffect, useState } from "react"
import { api } from "./api"
import { useApp } from "./state"

export function useFetch<T>(path: string) {
  const { version } = useApp()
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancel = false
    setLoading(true)
    api<T>(path)
      .then((next) => {
        if (!cancel) {
          setData(next)
          setError(null)
        }
      })
      .catch((reason: Error) => {
        if (!cancel) setError(reason.message)
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [path, version, tick])

  return { data, error, loading, reload: () => setTick((value) => value + 1) }
}
