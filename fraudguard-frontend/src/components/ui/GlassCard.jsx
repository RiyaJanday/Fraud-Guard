import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

export default function GlassCard({
  children,
  className,
  hover = true,
  delay = 0,
  as: Component = motion.div,
  ...props
}) {
  return (
    <Component
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      whileHover={hover ? { y: -4 } : undefined}
      className={cn(
        'glass-card p-5 transition-shadow duration-300',
        hover && 'hover:border-white/20 hover:shadow-[0_8px_50px_-10px_rgba(124,58,237,0.35)]',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  )
}
