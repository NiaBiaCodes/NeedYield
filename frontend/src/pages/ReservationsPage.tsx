import { Link } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { formatDateTime } from '../utils/reservations'

export function ReservationsPage() {
  const { reservations, simulateExpiration } = useApp()
  return <div className="page container reservations-page">
    <header className="page-header"><span className="kicker">YOUR PICKUPS</span><h1>My Reservations</h1><p>Reserved produce is held until 5:00 PM New York time on the day it is claimed.</p></header>
    <section className="rescue-callout"><div className="rescue-icon">↻</div><div><span className="kicker">RESCUE MODE</span><h2>A second chance for fresh food.</h2><p>Didn't make your pickup? Rescue Mode releases unclaimed produce so another neighbor has a chance to use it before it goes to waste.</p></div></section>
    {!reservations.length ? <div className="empty-state"><span>🧺</span><h2>No reservations yet</h2><p>Find fresh produce available at a demo location near you.</p><Link className="button button-primary" to="/find-food">Find Fresh Food</Link></div> : <div className="reservation-list">{reservations.map((reservation) => <article className="reservation-card" key={reservation.id}>
      <div><span className={`status status-${reservation.status.toLowerCase()}`}>{reservation.status.replace('_', ' ')}</span><h2>{reservation.quantity} × {reservation.produce}</h2><p><strong>{reservation.locationName}</strong><br />{reservation.locationAddress}</p></div>
      <dl><div><dt>Reserved</dt><dd>{formatDateTime(reservation.reservedAt)}</dd></div><div><dt>Pickup deadline</dt><dd>{formatDateTime(reservation.expiresAt)}</dd></div></dl>
      {reservation.status === 'RESERVED' && <details className="demo-tools"><summary>Demo controls</summary><p>Simulate a missed pickup to verify Rescue Mode.</p><button className="text-button danger" onClick={() => void simulateExpiration(reservation.id)}>Simulate expiration</button></details>}
      {reservation.status === 'EXPIRED' && <p className="released-note">Rescue Mode returned this produce to available inventory.</p>}
    </article>)}</div>}
  </div>
}
