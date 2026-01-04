import { useState, useEffect } from 'react'
import Header from '@/components/Header'
import RecentTrades from '@/components/RecentTrades'
import { exchangeApi } from '@/lib/api'

export default function Trades() {
  const [connectionId, setConnectionId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Set default connection immediately to prevent infinite loading
    setConnectionId(6)
    setLoading(false)
    
    // Try to fetch connections in background (non-blocking)
    const fetchConnections = async () => {
      try {
        const response = await exchangeApi.getConnections()
        const conns = response?.connections || []
        if (conns.length > 0) {
          setConnectionId(conns[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch connections:', error)
        // Keep default connection ID 6
      }
    }

    // Fetch in background, don't block UI
    fetchConnections()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary">
        <Header />
        <div className="container mx-auto px-6 py-8">
          <div className="text-center text-text-secondary">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Header />
      <main className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-6 sm:py-8 animate-fade-in-up">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">Trades</h1>
          <p className="text-text-muted text-sm">View your trading history and execution details</p>
        </div>
        {connectionId && <RecentTrades connectionId={connectionId} />}
      </main>
    </div>
  )
}

