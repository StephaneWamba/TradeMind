import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Strategies from './pages/Strategies'
import Trades from './pages/Trades'
import Analytics from './pages/Analytics'
import LLMLogs from './pages/LLMLogs'
import Backtest from './pages/Backtest'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/trades" element={<Trades />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/llm-logs" element={<LLMLogs />} />
        <Route path="/backtest" element={<Backtest />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

