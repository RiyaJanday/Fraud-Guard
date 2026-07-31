import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, initializing } = useAuth()

  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-primary" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  return children
}
