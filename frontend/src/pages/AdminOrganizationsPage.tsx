import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { approveOrganization, getOrganizationApplications, rejectOrganization, type OrganizationApplication } from '../services/api'

export function AdminOrganizationsPage() {
  const { user } = useAuth(); const [items, setItems] = useState<OrganizationApplication[]>([]); const [error, setError] = useState(''); const refresh = () => getOrganizationApplications().then(setItems).catch((e) => setError(e.message))
  useEffect(() => { if (user?.isAdmin) refresh() }, [user])
  if (!user?.isAdmin) return <Navigate to="/account" replace />
  const approve = async (item: OrganizationApplication) => { const lat = Number(prompt('Verified latitude', '40.7917')); const lon = Number(prompt('Verified longitude', '-73.9462')); if (!Number.isFinite(lat) || !Number.isFinite(lon)) return; await approveOrganization(item.id, lat, lon); refresh() }
  const reject = async (item: OrganizationApplication) => { const note = prompt('What information is missing?'); if (!note) return; await rejectOrganization(item.id, note); refresh() }
  return <div className="page container"><div className="page-title"><span className="kicker">ADMIN</span><h1>Organization approvals</h1><p>Verify identity, address, operating capacity, and coordinates before allowing donations.</p></div>{error && <p className="workflow-error">{error}</p>}<div className="approval-list">{items.length === 0 && <div className="empty-state"><h2>No applications yet</h2></div>}{items.map((item) => <article key={item.id}><div><span className="status status-released">{item.status}</span><h2>{item.organization_name}</h2><p>{item.organization_type} · {item.address} · {item.neighborhood}, {item.borough}</p><p><strong>{item.contact_name}</strong> · {item.email} · {item.phone}</p><small>Accepts: {item.accepted_categories.join(', ')}</small></div>{item.status === 'PENDING' && <div className="approval-actions"><button className="button button-dark" onClick={() => approve(item)}>Verify & approve</button><button className="text-button danger" onClick={() => reject(item)}>Request changes</button></div>}</article>)}</div></div>
}
