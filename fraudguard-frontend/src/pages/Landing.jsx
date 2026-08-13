import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import AnimatedNumber from '../components/ui/AnimatedNumber'
import {
  ShieldCheck, ArrowRight, Zap, BrainCircuit, Radar, Lock,
  BarChart3, Sparkles, CheckCircle2,
} from 'lucide-react'
import GradientBlobs from '../components/ui/GradientBlobs'
import RiskGauge from '../components/ui/RiskGauge'

const FEATURES = [
  { icon: Zap, title: 'Real-Time Scoring', desc: 'Every transaction scored in under 40ms using an ensemble of gradient-boosted and deep sequence models.' },
  { icon: BrainCircuit, title: 'Explainable AI', desc: 'SHAP-powered breakdowns show exactly which signals drove every fraud decision — built for auditors.' },
  { icon: Radar, title: 'Live Monitoring', desc: 'Watch transactions stream in with instant alerts the moment risk crosses your defined thresholds.' },
  { icon: BarChart3, title: 'Deep Analytics', desc: 'Merchant, geography and behavioral analytics to spot emerging fraud rings before they scale.' },
  { icon: Lock, title: 'Bank-Grade Security', desc: 'SOC 2 Type II, PCI-DSS Level 1 compliant infrastructure with end-to-end encryption.' },
  { icon: Sparkles, title: 'Adaptive Learning', desc: 'Models retrain continuously on confirmed outcomes, adapting to new fraud patterns automatically.' },
]

const STEPS = [
  { title: 'Connect your payment stream', desc: 'Drop in our SDK or REST API — live in under an hour, no infrastructure changes required.' },
  { title: 'Model scores every transaction', desc: 'Our ensemble evaluates 200+ behavioral, device and network signals in real time.' },
  { title: 'Act with confidence', desc: 'Approve, challenge with MFA, or block — each decision backed by a transparent explanation.' },
]

const STATS = [
  { value: 99.7, suffix: '%', decimals: 1, label: 'Detection accuracy' },
  { value: 38, suffix: 'ms', label: 'Median scoring latency' },
  { value: 2.4, suffix: 'B+', decimals: 1, label: 'Transactions protected' },
  { value: 340, suffix: 'M', label: 'Fraud losses prevented' },
]

export default function Landing() {
  return (
    <div className="relative overflow-hidden">
      <GradientBlobs />

      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-white/5 bg-bg/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-glow">
              <ShieldCheck size={18} className="text-white" />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight">FraudGuard</span>
          </div>
          <nav className="hidden items-center gap-8 text-sm text-white/60 md:flex">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#how-it-works" className="hover:text-white">How it works</a>
            <a href="#stats" className="hover:text-white">Results</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" className="hidden text-sm font-medium text-white/70 hover:text-white sm:block">
              Log in
            </Link>
            <Link to="/register" className="btn-primary text-sm">
              Get Started <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-6 pb-24 pt-20 lg:grid-cols-2 lg:pt-28">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1.5 text-xs font-medium text-primary">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
            </span>
            AI Model v4.2.1 · Live in production
          </div>
          <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-6xl">
            Stop credit card fraud
            <span className="text-gradient"> before it happens.</span>
          </h1>
          <p className="mt-6 max-w-lg text-base leading-relaxed text-white/50 sm:text-lg">
            FraudGuard scores every transaction in real time with an explainable AI engine trusted by banks and
            fintechs to catch fraud without blocking good customers.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link to="/register" className="btn-primary">
              Start Free Trial <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="btn-ghost">
              View Live Demo
            </Link>
          </div>
          <div className="mt-10 flex items-center gap-6 text-xs text-white/30">
            <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-success" /> SOC 2 Type II</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-success" /> PCI-DSS Level 1</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-success" /> GDPR Ready</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="glass-card relative p-6"
        >
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-xs text-white/40">Transaction Risk Assessment</p>
              <p className="font-mono text-sm text-white/70">TXN-8F21A-9034</p>
            </div>
            <span className="badge-danger">Blocked</span>
          </div>
          <div className="flex justify-center py-2">
            <RiskGauge value={87} size={220} />
          </div>
          <div className="mt-4 space-y-2.5 border-t border-white/10 pt-4">
            {[
              { label: 'Transaction velocity', impact: 0.31 },
              { label: 'Geo mismatch detected', impact: 0.24 },
              { label: 'New device fingerprint', impact: 0.18 },
            ].map((f) => (
              <div key={f.label}>
                <div className="flex justify-between text-xs">
                  <span className="text-white/60">{f.label}</span>
                  <span className="text-danger">+{f.impact}</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${f.impact * 220}%` }}
                    transition={{ duration: 1, delay: 0.4 }}
                    className="h-full rounded-full bg-danger"
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Stats */}
      <section id="stats" className="border-y border-white/5 bg-white/[0.015] py-14">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-8 px-6 lg:grid-cols-4">
          {STATS.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="text-center"
            >
              <p className="font-display text-3xl font-semibold text-white sm:text-4xl">
                <AnimatedNumber value={s.value} decimals={s.decimals || 0} duration={2} suffix={s.suffix} />
              </p>
              <p className="mt-1 text-sm text-white/40">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-7xl px-6 py-24">
        <div className="mb-14 text-center">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-primary/80">Platform</p>
          <h2 className="font-display text-3xl font-semibold sm:text-4xl">Everything you need to fight fraud</h2>
          <p className="mx-auto mt-3 max-w-xl text-white/45">
            A complete detection, explainability and monitoring stack — built for teams that move fast.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: (i % 3) * 0.08 }}
              whileHover={{ y: -4 }}
              className="glass-card p-6 hover:border-primary/30"
            >
              <div className="mb-4 w-fit rounded-xl border border-white/10 bg-gradient-to-br from-primary/20 to-accent/10 p-3 text-primary">
                <f.icon size={20} />
              </div>
              <h3 className="font-display text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/45">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-white/5 bg-white/[0.015] py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-14 text-center">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-primary/80">Workflow</p>
            <h2 className="font-display text-3xl font-semibold sm:text-4xl">From transaction to decision in milliseconds</h2>
          </div>
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            {STEPS.map((s, i) => (
              <motion.div
                key={s.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="relative"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary font-display text-lg font-semibold shadow-glow">
                  {i + 1}
                </div>
                <h3 className="font-display text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/45">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="glass-card relative overflow-hidden p-12"
        >
          <h2 className="font-display text-3xl font-semibold sm:text-4xl">Ready to stop fraud in real time?</h2>
          <p className="mx-auto mt-3 max-w-md text-white/45">
            Join fintechs and banks already protecting billions in transaction volume with FraudGuard.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link to="/register" className="btn-primary">
              Start Free Trial <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="btn-ghost">Log In</Link>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 px-6 py-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2 text-sm text-white/40">
            <ShieldCheck size={16} className="text-primary" /> FraudGuard © 2026. All rights reserved.
          </div>
          {/* Social icons removed: no real destinations exist for them yet
              (no GitHub/Twitter/Discord presence). Add back with real hrefs
              once those exist — dead icon links are worse than no icons. */}
        </div>
      </footer>
    </div>
  )
}
