import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ShieldCheck, Mail, Lock, User, Building2, Eye, EyeOff, ArrowRight, CheckCircle2 } from 'lucide-react'
import GradientBlobs from '../components/ui/GradientBlobs'
import { useAuth } from '../context/AuthContext'
import { getApiErrorMessage } from '../lib/api'

const schema = z
  .object({
    name: z.string().min(2, 'Enter your full name'),
    org: z.string().min(2, 'Organization is required'),
    email: z.string().email('Enter a valid email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[a-zA-Z]/, 'Password must contain a letter')
      .regex(/[0-9]/, 'Password must contain a digit'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

const PERKS = ['14-day free trial, no card required', 'Full SHAP explainability included', 'Unlimited team seats in trial']

export default function Register() {
  const [showPassword, setShowPassword] = useState(false)
  const { register: registerUser, loading } = useAuth()
  const navigate = useNavigate()

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })

  const onSubmit = async (data) => {
    try {
      await registerUser({ full_name: data.name, email: data.email, password: data.password })
      toast.success('Account created — welcome to FraudGuard')
      navigate('/dashboard')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not create account'))
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
          <h1 className="font-display text-2xl font-semibold">Create your account</h1>
          <p className="mt-1.5 text-sm text-white/45">Start detecting fraud in real time within minutes.</p>

          <div className="mt-4 space-y-1.5">
            {PERKS.map((p) => (
              <div key={p} className="flex items-center gap-2 text-xs text-white/40">
                <CheckCircle2 size={13} className="text-success" /> {p}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-white/50">Full Name</label>
                <div className="relative">
                  <User size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                  <input {...register('name')} defaultValue="Aarav Mehta" placeholder="Jane Doe" className="input-glass pl-10" />
                </div>
                {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-white/50">Organization</label>
                <div className="relative">
                  <Building2 size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                  <input {...register('org')} defaultValue="NovaBank" placeholder="Acme Inc." className="input-glass pl-10" />
                </div>
                {errors.org && <p className="mt-1 text-xs text-danger">{errors.org.message}</p>}
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Work Email</label>
              <div className="relative">
                <Mail size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input {...register('email')} defaultValue="aarav.mehta@fraudguard.ai" placeholder="you@company.com" className="input-glass pl-10" />
              </div>
              {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-white/50">Password</label>
                <div className="relative">
                  <Lock size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    defaultValue="fraudguard123"
                    placeholder="••••••••"
                    className="input-glass pl-10 pr-10"
                  />
                  <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60">
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-white/50">Confirm Password</label>
                <div className="relative">
                  <Lock size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                  <input
                    {...register('confirmPassword')}
                    type={showPassword ? 'text' : 'password'}
                    defaultValue="fraudguard123"
                    placeholder="••••••••"
                    className="input-glass pl-10"
                  />
                </div>
                {errors.confirmPassword && <p className="mt-1 text-xs text-danger">{errors.confirmPassword.message}</p>}
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Creating account...' : 'Create Account'} <ArrowRight size={16} />
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-white/40">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-primary hover:text-primary-400">
            Log in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
