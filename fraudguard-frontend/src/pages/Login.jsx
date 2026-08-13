import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ShieldCheck, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react'
import GradientBlobs from '../components/ui/GradientBlobs'
import { useAuth } from '../context/AuthContext'
import { getApiErrorMessage } from '../lib/api'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

export default function Login() {
  const [showPassword, setShowPassword] = useState(false)
  const { login, loading } = useAuth()
  const navigate = useNavigate()

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })

  const onSubmit = async (data) => {
    try {
      await login(data.email, data.password)
      toast.success('Welcome back to FraudGuard')
      navigate('/dashboard')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Invalid email or password'))
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-12">
      <GradientBlobs variant="auth" />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Link to="/" className="mb-8 flex items-center justify-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-glow">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <span className="font-display text-xl font-semibold">FraudGuard</span>
        </Link>

        <div className="glass-card p-8">
          <h1 className="font-display text-2xl font-semibold">Welcome back</h1>
          <p className="mt-1.5 text-sm text-white/45">Log in to your fraud monitoring dashboard.</p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-7 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Email Address</label>
              <div className="relative">
                <Mail size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  {...register('email')}
                  placeholder="you@company.com"
                  className="input-glass pl-10"
                />
              </div>
              {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="block text-xs font-medium text-white/50">Password</label>
                <Link to="/forgot-password" className="text-xs text-primary/80 hover:text-primary">Forgot password?</Link>
              </div>
              <div className="relative">
                <Lock size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="input-glass pl-10 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Signing in...' : 'Log In'} <ArrowRight size={16} />
            </button>
          </form>

          {/* Google / SSO sign-in removed: no OAuth backend is wired up yet.
              Re-add this block once /auth/google or /auth/saml exist server-side. */}
        </div>

        <p className="mt-6 text-center text-sm text-white/40">
          Don't have an account?{' '}
          <Link to="/register" className="font-medium text-primary hover:text-primary-400">
            Create one
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
