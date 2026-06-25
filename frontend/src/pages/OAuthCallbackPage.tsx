// src/pages/OAuthCallbackPage.tsx
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { PageLoader } from '@/components/ui'

export default function OAuthCallbackPage() {
  const { login } = useAuth()
  const navigate  = useNavigate()
  const [params]  = useSearchParams()

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      toast.error('Sign-in failed. Please try again.')
      navigate('/login', { replace: true })
      return
    }
    localStorage.setItem('token', token)
    authApi.me()
      .then(res => {
        login(token, res.data)
        toast.success(`Welcome, ${res.data.full_name?.split(' ')[0] || 'there'}`)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        localStorage.removeItem('token')
        toast.error('Could not load profile. Please try again.')
        navigate('/login', { replace: true })
      })
  }, [params, login, navigate])

  return <PageLoader />
}
