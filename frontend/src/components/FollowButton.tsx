import { api } from "../api"
import { useApp } from "../state"
import { Button } from "./ui/button"

export function FollowButton({
  targetType,
  slug,
  followed,
  onChange,
}: {
  targetType: "title" | "person" | "studio" | "franchise"
  slug: string
  followed: boolean
  onChange?: () => void
}) {
  const { bump } = useApp()

  async function toggle() {
    if (followed) {
      await api(`/api/follows/${targetType}/${slug}`, { method: "DELETE" })
    } else {
      await api("/api/follows", { method: "POST", body: JSON.stringify({ target_type: targetType, slug }) })
    }
    bump()
    onChange?.()
  }

  return (
    <Button variant={followed ? "outline" : "default"} onClick={toggle}>
      {followed ? "Following" : "Follow"}
    </Button>
  )
}
