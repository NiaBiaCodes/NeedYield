import { useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { Brand } from './Brand'
import { useAuth } from '../context/AuthContext'

export function Layout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const { user } = useAuth()
  const navItems = user?.isAdmin
    ? [{ to: '/admin/organizations', label: 'Approvals' }, { to: '/find-food', label: 'Find Food' }, { to: '/about', label: 'About' }]
    : user?.role === 'organization'
    ? [{ to: '/organization', label: 'Organization Portal' }, { to: '/find-food', label: 'Find Food' }, { to: '/assistant', label: 'AI Assistant' }, { to: '/about', label: 'About' }]
    : user?.role === 'gardener'
    ? [{ to: '/donate', label: 'Donate' }, { to: '/donations', label: 'My Donations' }, { to: '/assistant', label: 'AI Assistant' }, { to: '/about', label: 'About' }]
    : [{ to: '/find-food', label: 'Find Food' }, { to: '/reservations', label: 'My Reservations' }, { to: '/assistant', label: 'AI Assistant' }, { to: '/about', label: 'About' }]
  return <div className="app-shell">
    <header className="site-header">
      <nav className="nav container" aria-label="Main navigation">
        <Brand />
        <button className="menu-button" aria-expanded={open} aria-label="Toggle navigation" onClick={() => setOpen(!open)}>☰</button>
        <div className={`nav-links ${open ? 'open' : ''}`}>
          {navItems.map((item) => <NavLink key={item.to} to={item.to} onClick={() => setOpen(false)}>{item.label}</NavLink>)}
          <NavLink className="account-link" to={user ? '/account' : '/auth'} onClick={() => setOpen(false)}>{user ? `${user.displayName}${user.demo ? ' · Demo' : ''}` : 'Sign in'}</NavLink>
        </div>
      </nav>
    </header>
    <main>{children}</main>
    <footer className="site-footer">
      <div className="container footer-inner"><Brand /><p>Matching New York's yield with New York's need.</p><span>Hackathon demo · 2026</span></div>
    </footer>
  </div>
}
