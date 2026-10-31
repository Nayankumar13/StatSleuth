import { NavLink, Route, Routes } from 'react-router-dom'
import Analyze from './pages/Analyze'
import Report from './pages/Report'
import Tools from './pages/Tools'
import History from './pages/History'
import Method from './pages/Method'

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--accent)" />
      <circle cx="14" cy="14" r="6" fill="none" stroke="#fff" strokeWidth="3" />
      <path d="M19 19l7 7" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export default function App() {
  return (
    <>
      <a href="#main" className="skip">Skip to content</a>
      <header className="nav">
        <NavLink to="/" className="brand"><Logo /> StatSleuth</NavLink>
        <nav aria-label="Main">
          <NavLink to="/" end>Analyse</NavLink>
          <NavLink to="/tools">Quick checks</NavLink>
          <NavLink to="/history">History</NavLink>
          <NavLink to="/method">Method &amp; limits</NavLink>
        </nav>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Analyze />} />
          <Route path="/report/:id" element={<Report />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/history" element={<History />} />
          <Route path="/method" element={<Method />} />
          <Route path="*" element={<div className="page"><h1>Page not found</h1></div>} />
        </Routes>
      </main>
      <footer className="foot">StatSleuth · built for THREWS ODYSSEY 2026 · consistency checks, not accusations</footer>
    </>
  )
}
