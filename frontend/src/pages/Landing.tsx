import { Link } from 'react-router-dom'
import { 
  Brain, 
  Shield, 
  BarChart3, 
  Zap, 
  TestTube,
  ArrowRight,
  Github,
  Linkedin,
  Activity,
  Lock
} from 'lucide-react'

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-bg-primary via-bg-secondary to-bg-primary">
      {/* Top Bar with Social Links and Portfolio Badge */}
      <div className="border-b border-border-divider bg-bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="px-3 py-1 bg-accent-warning/20 text-accent-warning rounded-full text-xs font-semibold border border-accent-warning/30">
                📁 Portfolio Project
              </span>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/StephaneWamba/TradeMind"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-bg-elevated hover:bg-bg-elevated/80 border border-border-default rounded-lg text-text-primary transition-colors group"
              >
                <Github className="w-4 h-4 group-hover:text-accent-primary transition-colors" />
                <span className="text-sm font-medium">GitHub</span>
              </a>
              <a
                href="https://www.linkedin.com/in/stephane-wamba/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-bg-elevated hover:bg-bg-elevated/80 border border-border-default rounded-lg text-text-primary transition-colors group"
              >
                <Linkedin className="w-4 h-4 group-hover:text-accent-primary transition-colors" />
                <span className="text-sm font-medium">LinkedIn</span>
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-32 bg-bg-primary">
        <div className="absolute inset-0">
          <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-accent-primary/5 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-accent-secondary/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        </div>
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary/10 border border-accent-primary/20 rounded-full mb-6">
              <Activity className="w-4 h-4 text-accent-primary" />
              <span className="text-sm font-medium text-accent-primary">AI-Powered Bitcoin Trading</span>
            </div>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-text-primary mb-6 leading-tight">
              TradeMind
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-accent-primary to-accent-secondary mt-2">
                Autonomous Trading Platform
              </span>
            </h1>
            <p className="text-xl sm:text-2xl text-text-secondary mb-8 leading-relaxed">
              Leverage AI, real-time market analysis, and advanced risk management 
              to trade Bitcoin with confidence. Built for serious traders.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/dashboard"
                className="group px-8 py-4 bg-accent-primary text-white rounded-lg font-semibold text-lg hover:bg-accent-primary/90 transition-all transform hover:scale-105 shadow-lg shadow-accent-primary/20 flex items-center gap-2"
              >
                Launch Platform
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <a
                href="https://github.com/StephaneWamba/TradeMind"
                target="_blank"
                rel="noopener noreferrer"
                className="px-8 py-4 bg-bg-card border-2 border-border-default text-text-primary rounded-lg font-semibold text-lg hover:border-accent-primary transition-all flex items-center gap-2"
              >
                <Github className="w-5 h-5" />
                View Source Code
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-bg-secondary/30">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-16 xl:px-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold text-text-primary mb-4">
              Powerful Features for Modern Trading
            </h2>
            <p className="text-xl text-text-secondary max-w-2xl mx-auto">
              Everything you need to trade Bitcoin autonomously with AI-powered insights
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="group p-8 bg-bg-card border border-border-default rounded-xl hover:border-accent-primary transition-all hover:shadow-lg hover:shadow-accent-primary/10">
              <div className="w-14 h-14 bg-accent-primary/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-accent-primary/20 transition-colors">
                <Brain className="w-7 h-7 text-accent-primary" />
              </div>
              <h3 className="text-2xl font-bold text-text-primary mb-3">AI-Powered Decisions</h3>
              <p className="text-text-secondary leading-relaxed">
                Grok AI analyzes market data, news, and social sentiment to make intelligent trading decisions. 
                Real-time web and X (Twitter) search for comprehensive market intelligence.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group p-8 bg-bg-card border border-border-default rounded-xl hover:border-accent-primary transition-all hover:shadow-lg hover:shadow-accent-primary/10">
              <div className="w-14 h-14 bg-accent-success/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-accent-success/20 transition-colors">
                <Shield className="w-7 h-7 text-accent-success" />
              </div>
              <h3 className="text-2xl font-bold text-text-primary mb-3">Advanced Risk Management</h3>
              <p className="text-text-secondary leading-relaxed">
                Circuit breakers, daily loss limits, portfolio heat tracking, and position sizing 
                algorithms protect your capital. Trailing stop-loss and OCO orders for maximum control.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group p-8 bg-bg-card border border-border-default rounded-xl hover:border-accent-primary transition-all hover:shadow-lg hover:shadow-accent-primary/10">
              <div className="w-14 h-14 bg-accent-info/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-accent-info/20 transition-colors">
                <BarChart3 className="w-7 h-7 text-accent-info" />
              </div>
              <h3 className="text-2xl font-bold text-text-primary mb-3">Real-Time Analytics</h3>
              <p className="text-text-secondary leading-relaxed">
                Live charts with technical indicators (RSI, MACD, ATR, Bollinger Bands), 
                multi-timeframe analysis, and comprehensive performance metrics.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="group p-8 bg-bg-card border border-border-default rounded-xl hover:border-accent-primary transition-all hover:shadow-lg hover:shadow-accent-primary/10">
              <div className="w-14 h-14 bg-accent-warning/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-accent-warning/20 transition-colors">
                <Zap className="w-7 h-7 text-accent-warning" />
              </div>
              <h3 className="text-2xl font-bold text-text-primary mb-3">Autonomous Trading</h3>
              <p className="text-text-secondary leading-relaxed">
                Set it and forget it. Automated strategy execution every 15 minutes with 
                confidence thresholds and risk checks. Full control via API or UI.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="group p-8 bg-bg-card border border-border-default rounded-xl hover:border-accent-primary transition-all hover:shadow-lg hover:shadow-accent-primary/10">
              <div className="w-14 h-14 bg-accent-secondary/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-accent-secondary/20 transition-colors">
                <TestTube className="w-7 h-7 text-accent-secondary" />
              </div>
              <h3 className="text-2xl font-bold text-text-primary mb-3">Backtesting Engine</h3>
              <p className="text-text-secondary leading-relaxed">
                Test strategies on historical data with LLM-powered decision simulation. 
                Comprehensive metrics: Sharpe ratio, drawdown, win rate, and more.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="group p-8 bg-bg-card border border-border-default rounded-xl hover:border-accent-primary transition-all hover:shadow-lg hover:shadow-accent-primary/10">
              <div className="w-14 h-14 bg-accent-danger/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-accent-danger/20 transition-colors">
                <Lock className="w-7 h-7 text-accent-danger" />
              </div>
              <h3 className="text-2xl font-bold text-text-primary mb-3">Enterprise Security</h3>
              <p className="text-text-secondary leading-relaxed">
                Secure API key management, encrypted connections, and comprehensive 
                audit logs. Email alerts for critical events and system monitoring.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-16 xl:px-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold text-text-primary mb-4">
              Built with Modern Technology
            </h2>
            <p className="text-xl text-text-secondary max-w-2xl mx-auto">
              A robust, scalable architecture for production-grade trading
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
            {[
              'FastAPI', 'React', 'PostgreSQL', 'Redis', 'Celery', 'Docker',
              'Grok AI', 'Tavily', 'WebSocket', 'TypeScript', 'Tailwind', 'SQLAlchemy'
            ].map((tech) => (
              <div
                key={tech}
                className="p-6 bg-bg-card border border-border-default rounded-lg text-center hover:border-accent-primary transition-colors"
              >
                <span className="text-text-primary font-semibold">{tech}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-r from-accent-primary/10 via-accent-secondary/10 to-accent-primary/10">
        <div className="max-w-4xl mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 text-center">
          <h2 className="text-4xl sm:text-5xl font-bold text-text-primary mb-6">
            Ready to Start Trading?
          </h2>
          <p className="text-xl text-text-secondary mb-8">
            Experience the future of autonomous Bitcoin trading. 
            Built for traders who demand precision and control.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-10 py-5 bg-accent-primary text-white rounded-lg font-bold text-lg hover:bg-accent-primary/90 transition-all transform hover:scale-105 shadow-lg shadow-accent-primary/30"
          >
            Launch TradeMind Platform
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-divider py-12 bg-bg-card/50">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-16 xl:px-20">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-text-secondary text-sm">
              <p className="font-semibold text-text-primary mb-1">TradeMind</p>
              <p>Autonomous Bitcoin Trading Platform</p>
              <p className="mt-2 text-xs">© 2026 Stephane Wamba - Portfolio Project</p>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/StephaneWamba/TradeMind"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 bg-bg-elevated hover:bg-bg-elevated/80 border border-border-default rounded-lg text-text-primary transition-colors"
                aria-label="GitHub"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="https://www.linkedin.com/in/stephane-wamba/"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 bg-bg-elevated hover:bg-bg-elevated/80 border border-border-default rounded-lg text-text-primary transition-colors"
                aria-label="LinkedIn"
              >
                <Linkedin className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

