import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ShieldCheck, Mail, ArrowRight, ArrowLeft } from 'lucide-react'
import GradientBlobs from '../components/ui/GradientBlobs'
import { fraudApi, getApiErrorMessage } from '../lib/api'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
})

export default function ForgotPassword() {
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  // Only populated by the backend outside production (no email provider is
  // wired up yet) — see ForgotPasswordResponse.dev_reset_token. In
  // production this stays null and the generic message is all we show.
  const [devResetToken, setDevResetToken] = useState(null)
  const navigate = useNavigate()

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      const { data: res } = await fraudApi.forgotPassword(data.email)
      setDevResetToken(res.dev_reset_token || null)
      setSubmitted(true)
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not process that request'))
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
          {!submitted ? (
            <>
              <h1 className="font-display text-2xl font-semibold">Reset your password</h1>
              <p className="mt-1.5 text-sm text-white/45">
                Enter your account email and we'll send you a link to reset your password.
              </p>

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

                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading ? 'Sending...' : 'Send reset link'} <ArrowRight size={16} />
                </button>
              </form>
            </>
          ) : (
            <>
              <h1 className="font-display text-2xl font-semibold">Check your email</h1>
              <p className="mt-1.5 text-sm text-white/45">
                If an account with that email exists, we've sent a link to reset your password.
              </p>

              {devResetToken && (
                <div className="mt-5 rounded-xl border border-warning/30 bg-warning/10 p-4">
                  <p className="text-xs font-medium text-warning">Dev environment only</p>
                  <p className="mt-1 text-xs text-white/50">
                    No email provider is wired up yet, so the reset token is shown here directly for testing.
                  </p>
                  <button
                    type="button"
                    onClick={() => navigate(`/reset-password?token=${encodeURIComponent(devResetToken)}`)}
                    className="btn-primary mt-3 w-full text-sm"
                  >
                    Continue to reset password <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <p className="mt-6 flex items-center justify-center gap-1.5 text-center text-sm text-white/40">
          <ArrowLeft size={14} />
          <Link to="/login" className="font-medium text-primary hover:text-primary-400">
            Back to log in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
