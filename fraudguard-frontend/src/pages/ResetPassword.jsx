import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ShieldCheck, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react'
import GradientBlobs from '../components/ui/GradientBlobs'
import { fraudApi, getApiErrorMessage } from '../lib/api'

const schema = z
  .object({
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

export default function ResetPassword() {
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const navigate = useNavigate()

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })

  const onSubmit = async (data) => {
    if (!token) {
      toast.error('Missing or invalid reset link. Please request a new one.')
      return
    }
    setLoading(true)
    try {
      await fraudApi.resetPassword(token, data.password)
      toast.success('Password reset — please log in')
      navigate('/login')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not reset password. The link may have expired.'))
    } finally {
      setLoading(false)
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
          <h1 className="font-display text-2xl font-semibold">Set a new password</h1>
          <p className="mt-1.5 text-sm text-white/45">Choose a new password for your account.</p>

          {!token && (
            <p className="mt-4 rounded-xl border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
              This link is missing its reset token. Please request a new password reset link.
            </p>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-7 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">New Password</label>
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

            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Confirm New Password</label>
              <div className="relative">
                <Lock size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  {...register('confirmPassword')}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="input-glass pl-10"
                />
              </div>
              {errors.confirmPassword && <p className="mt-1 text-xs text-danger">{errors.confirmPassword.message}</p>}
            </div>

            <button type="submit" disabled={loading || !token} className="btn-primary w-full disabled:opacity-50">
              {loading ? 'Resetting...' : 'Reset password'} <ArrowRight size={16} />
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-white/40">
          Remembered it after all?{' '}
          <Link to="/login" className="font-medium text-primary hover:text-primary-400">
            Log in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
