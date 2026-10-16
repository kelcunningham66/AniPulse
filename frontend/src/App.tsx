import { BrowserRouter, Route, Routes } from "react-router-dom"
import { Shell } from "./components/Shell"
import { Alerts } from "./pages/Alerts"
import { Ask } from "./pages/Ask"
import { CalendarPage } from "./pages/CalendarPage"
import { CatchUp } from "./pages/CatchUp"
import { Dashboard } from "./pages/Dashboard"
import { Discover } from "./pages/Discover"
import { EntityPage } from "./pages/EntityPage"
import { Feed } from "./pages/Feed"
import { Pulse } from "./pages/Pulse"
import { TitlePage } from "./pages/TitlePage"
import { AppState } from "./state"

export default function App() {
  return (
    <BrowserRouter>
      <AppState>
        <Shell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/feed" element={<Feed />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/ask" element={<Ask />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/catch-up" element={<CatchUp />} />
            <Route path="/discover" element={<Discover />} />
            <Route path="/pulse" element={<Pulse />} />
            <Route path="/title/:slug" element={<TitlePage />} />
            <Route path="/studio/:slug" element={<EntityPage kind="studio" />} />
            <Route path="/person/:slug" element={<EntityPage kind="person" />} />
            <Route path="/franchise/:slug" element={<EntityPage kind="franchise" />} />
          </Routes>
        </Shell>
      </AppState>
    </BrowserRouter>
  )
}
