import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { api } from "./api"
import type { Me } from "./types"

type AppContextValue = {
  me: Me | null
  loading: boolean
  error: string | null
  version: number
  refresh: () => Promise<void>
  bump: () => void
  patchMe: (body: Partial<Me>) => Promise<void>
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppState({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [version, setVersion] = useState(0)

  const refresh = useCallback(async () => {
    const next = await api<Me>("/api/me")
    setMe(next)
    setError(null)
    setVersion((value) => value + 1)
  }, [])

  useEffect(() => {
    let cancel = false
    api<Me>("/api/me")
      .then((next) => {
        if (!cancel) {
          setMe(next)
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
  }, [])

  const bump = useCallback(() => setVersion((value) => value + 1), [])

  const patchMe = useCallback(async (body: Partial<Me>) => {
    const next = await api<Me>("/api/me", { method: "PATCH", body: JSON.stringify(body) })
    setMe(next)
    setVersion((value) => value + 1)
  }, [])

  const value = useMemo(
    () => ({ me, loading, error, version, refresh, bump, patchMe }),
    [me, loading, error, version, refresh, bump, patchMe],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const value = useContext(AppContext)
  if (!value) throw new Error("useApp must be used inside AppState")
  return value
}
