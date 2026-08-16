import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { FoodLocation } from '../types'
import { useApp } from '../context/AppContext'
import { directionsUrl } from '../utils/distance'
import { foodCategory } from '../utils/search'
import { useAuth } from '../context/AuthContext'

export function LocationCard({ location }: { location: FoodLocation }) {
  const { reserveProduce } = useApp()
  const { user } = useAuth()
  const navigate = useNavigate()
  const availableItems = location.inventory.filter((item) => item.quantity > 0)
  const [produce, setProduce] = useState(availableItems[0]?.produce || '')
  const [quantity, setQuantity] = useState(1)
  const [message, setMessage] = useState('')
  const selected = location.inventory.find((item) => item.produce === produce)
  const categories = useMemo(() => ['Vegetables', 'Fruits', 'Herbs', 'Other produce'].map((name) => ({ name, items: location.inventory.filter((item) => foodCategory(item.produce) === name) })), [location.inventory])

  useEffect(() => {
    try {
      const pending = JSON.parse(sessionStorage.getItem('needyield-pending-reservation') || 'null')
      if (pending?.locationId === location.id) {
        setProduce(pending.produce); setQuantity(pending.quantity); setMessage('You are signed in. Review the selection and press Reserve to confirm.')
        sessionStorage.removeItem('needyield-pending-reservation')
        document.getElementById(`location-${location.id}`)?.scrollIntoView({ block: 'center' })
      }
    } catch { sessionStorage.removeItem('needyield-pending-reservation') }
  }, [location.id])

  async function handleReserve(event: React.FormEvent) {
    event.preventDefault()
    if (!user || user.role !== 'neighbor') {
      sessionStorage.setItem('needyield-pending-reservation', JSON.stringify({ locationId: location.id, produce, quantity }))
      navigate(`/auth?returnTo=${encodeURIComponent(`/find-food#location-${location.id}`)}`)
      return
    }
    try {
      await reserveProduce({ locationId: location.id, produce, quantity })
      setMessage(`${quantity} ${produce.toLowerCase()} reserved under ${user.email}. See My Reservations for pickup details.`)
      setQuantity(1)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to reserve right now.')
    }
  }

  return <article className="location-card" id={`location-${location.id}`}>
    <div className="card-topline"><span className="demo-badge">Demo location</span><span className="borough-tag">{location.borough}</span></div>
    <h2>{location.name}</h2>
    <p className="neighborhood">{location.neighborhood}</p>
    <p className="address">{location.address}</p>
    <div className="hours"><span aria-hidden="true">◷</span><span><strong>Pickup today</strong><br />{location.openingTime}–{location.closingTime}</span></div>
    <div className="inventory-categories" aria-label="Available demo inventory">{categories.map((category) => <details key={category.name}><summary><span>{category.name}</span><strong>{category.items.filter((item) => item.quantity > 0).length} available</strong></summary><div className="inventory-list">{category.items.length ? category.items.map((item) => <div className="inventory-row" key={item.produce}><span>{item.produce}</span><strong className={item.quantity === 0 ? 'sold-out' : ''}>{item.quantity ? `${item.quantity} available` : 'Claimed'}</strong></div>) : <p className="category-empty">No {category.name.toLowerCase()} listed today.</p>}</div></details>)}</div>
    {availableItems.length ? <form className="reserve-form" onSubmit={handleReserve}>
      <label>Produce<select value={produce} onChange={(event) => { setProduce(event.target.value); setQuantity(1); setMessage('') }}>
        {availableItems.map((item) => <option key={item.produce}>{item.produce}</option>)}
      </select></label>
      <label>Quantity<input type="number" min="1" max={selected?.quantity || 1} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label>
      <button className="button button-dark" type="submit">{!user || user.role !== 'neighbor' ? 'Sign in to reserve' : 'Reserve'}</button>
    </form> : <p className="empty-note">No produce is currently available here.</p>}
    <a className="directions-link" href={directionsUrl(location.latitude, location.longitude)} target="_blank" rel="noreferrer" aria-label={`Get directions to ${location.name}`}>Get Directions <span aria-hidden="true">↗</span></a>
    {message && <p className="form-message" role="status">{message}</p>}
  </article>
}
