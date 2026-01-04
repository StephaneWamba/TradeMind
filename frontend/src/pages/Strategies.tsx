import Header from '@/components/Header'
import StrategiesComponent from '@/components/Strategies'

export default function StrategiesPage() {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Header />
      <main className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-6 sm:py-8 animate-fade-in-up">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">Strategies</h1>
          <p className="text-text-muted text-sm">Manage and monitor your trading strategies</p>
        </div>
        <StrategiesComponent />
      </main>
    </div>
  )
}

