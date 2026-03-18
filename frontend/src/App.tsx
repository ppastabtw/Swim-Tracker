import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SwimmerSearchPage from './pages/SwimmerSearchPage'
import SwimmerProfilePage from './pages/SwimmerProfilePage'
import MeetPage from './pages/MeetPage'
import RankingsPage from './pages/RankingsPage'
import AdminToolsPage from './pages/AdminToolsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/swimmers" element={<SwimmerSearchPage />} />
      <Route path="/swimmers/:id" element={<SwimmerProfilePage />} />
      <Route path="/meets/:id" element={<MeetPage />} />
      <Route path="/rankings" element={<RankingsPage />} />
      <Route path="/admin-tools" element={<AdminToolsPage />} />
    </Routes>
  )
}
