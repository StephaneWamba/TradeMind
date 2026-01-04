import { cn } from '@/lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={cn(
      'bg-bg-card border border-border-default rounded-lg shadow-card',
      'hover:shadow-card-hover hover:border-border-hover',
      'transition-all duration-300 ease-out',
      'backdrop-blur-sm relative overflow-hidden',
      'before:absolute before:inset-0 before:bg-gradient-to-br before:from-white/0 before:via-white/0 before:to-white/5 before:pointer-events-none',
      className
    )}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: CardProps) {
  return (
    <div className={cn('px-6 pt-6 pb-4 border-b border-border-divider', className)}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className }: CardProps) {
  return (
    <h3 className={cn('text-lg font-semibold text-text-primary tracking-tight', className)}>
      {children}
    </h3>
  )
}

export function CardContent({ children, className }: CardProps) {
  return (
    <div className={cn('p-6', className)}>
      {children}
    </div>
  )
}


