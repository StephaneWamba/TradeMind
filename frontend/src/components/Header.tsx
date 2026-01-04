import { Link, useLocation } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Header() {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="bg-bg-card border-b border-border-default sticky top-0 z-50 backdrop-blur-sm bg-opacity-95 shadow-card">
      <div className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20">
        <div className="flex items-center justify-between h-16">
          <Link to="/dashboard" className="flex items-center gap-3 hover:opacity-90 transition-opacity group">
            <div className="bg-gradient-to-br from-accent-primary to-accent-secondary p-2 rounded-lg shadow-glow group-hover:shadow-glow transition-shadow">
              <Activity className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-text-primary tracking-tight">TradeMind</h1>
              <p className="text-xs text-text-muted hidden sm:block">Autonomous Trading</p>
            </div>
          </Link>
          
          <nav className="flex items-center gap-1 sm:gap-4 overflow-x-auto">
            <Link 
              to="/dashboard" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/dashboard') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              Dashboard
              {isActive('/dashboard') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
            <Link 
              to="/portfolio" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/portfolio') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              Portfolio
              {isActive('/portfolio') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
            <Link 
              to="/strategies" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/strategies') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              Strategies
              {isActive('/strategies') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
            <Link 
              to="/trades" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/trades') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              Trades
              {isActive('/trades') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
            <Link 
              to="/analytics" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/analytics') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              Analytics
              {isActive('/analytics') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
            <Link 
              to="/llm-logs" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/llm-logs') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              LLM Logs
              {isActive('/llm-logs') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
            <Link 
              to="/backtest" 
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap relative",
                isActive('/backtest') 
                  ? "text-accent-primary bg-bg-elevated border border-accent-primary/30 shadow-glow" 
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated border border-transparent"
              )}
            >
              Backtest
              {isActive('/backtest') && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-primary rounded-full" />
              )}
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}

