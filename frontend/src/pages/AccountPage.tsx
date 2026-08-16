import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function AccountPage() {
  const { user, signOut } = useAuth(); const navigate = useNavigate()
  if (!user) return <Navigate to="/auth" replace />
  return <div className="page container"><div className="account-card"><span className="account-avatar" aria-hidden="true">{user.displayName.charAt(0).toUpperCase()}</span><div><span className="kicker">{user.demo ? 'DEMO ACCOUNT' : 'NEEDYIELD ACCOUNT'}</span><h1>{user.displayName}</h1><p>{user.email}</p><span className="role-badge">{user.role}</span></div><div className="account-actions"><button className="button button-dark" onClick={() => navigate(user.role === 'gardener' ? '/donate' : '/find-food')}>{user.role === 'gardener' ? 'Donate produce' : 'Find fresh food'}</button><button className="text-button" onClick={async () => { await signOut(); navigate('/') }}>Sign out</button></div></div></div>
}
