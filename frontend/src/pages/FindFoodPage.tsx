import { useEffect, useMemo, useState } from 'react'
import { boroughs } from '../data/locations'
import { useApp } from '../context/AppContext'
import { LocationCard } from '../components/LocationCard'
import { FoodMap } from '../components/FoodMap'
import { fuzzyMatches, normalizeSearch } from '../utils/search'
import { getFoodMutualAidResources } from '../services/api'
import type { PublicResource } from '../types'

type LocationState = 'idle' | 'requesting' | 'available' | 'unavailable'

export function FindFoodPage() {
  const { locations } = useApp()
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [borough, setBorough] = useState('All boroughs')
  const [userLocation, setUserLocation] = useState<{ latitude: number; longitude: number } | null>(null)
  const [locationState, setLocationState] = useState<LocationState>('idle')
  const [resources, setResources] = useState<PublicResource[]>([])
  const [resourceSource, setResourceSource] = useState('Loading curated food resources…')
  useEffect(() => { getFoodMutualAidResources().then((result) => { setResources(result.resources); setResourceSource(result.source) }).catch(() => setResourceSource('Curated resources temporarily unavailable')) }, [])
  const filtered = useMemo(() => locations.filter((location) => {
    const search = normalizeSearch(appliedQuery)
    const matchesQuery = !search || location.inventory.some((item) => item.quantity > 0 && fuzzyMatches(search, item.produce)) || fuzzyMatches(search, location.neighborhood)
    return matchesQuery && (borough === 'All boroughs' || location.borough === borough)
  }), [locations, appliedQuery, borough])
  const filteredResources = useMemo(() => resources.filter((resource) => borough === 'All boroughs' || resource.borough === borough), [resources, borough])

  function requestLocation() {
    if (!navigator.geolocation) { setLocationState('unavailable'); return }
    setLocationState('requesting')
    navigator.geolocation.getCurrentPosition(
      (position) => { setUserLocation({ latitude: position.coords.latitude, longitude: position.coords.longitude }); setLocationState('available') },
      () => setLocationState('unavailable'),
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 300_000 },
    )
  }

  return <div className="page container">
    <header className="page-header"><span className="kicker">FRESH NEAR YOU</span><h1>Find food for today.</h1><p>Search demo inventory across New York City, compare pickup windows, and reserve what you need.</p></header>
    <div className="notice"><span>i</span><p><strong>Hackathon demo data</strong> — These locations and quantities are fictional and do not represent participating organizations.</p></div>
    <form className={`filters ${appliedQuery ? 'search-applied' : ''}`} aria-label="Food filters" onSubmit={(event) => { event.preventDefault(); setAppliedQuery(query) }}>
      <label className="search-field"><span>⌕</span><span className="sr-only">Search produce or neighborhood</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Try tomatoes, kale, or Harlem" /></label>
      <label><span className="sr-only">Filter by borough</span><select value={borough} onChange={(event) => setBorough(event.target.value)}>{boroughs.map((item) => <option key={item}>{item}</option>)}</select></label>
      <button className={`search-button ${appliedQuery ? 'active' : ''}`} type="submit">{appliedQuery ? 'Search again' : 'Search'}</button>
      <button className="location-button" type="button" onClick={requestLocation} disabled={locationState === 'requesting'}>{locationState === 'requesting' ? 'Locating…' : locationState === 'available' ? 'Location added ✓' : 'Use my location'}</button>
    </form>
    {appliedQuery && <div className="search-status" role="status"><span>Showing results for <strong>“{normalizeSearch(appliedQuery)}”</strong></span><button type="button" onClick={() => { setQuery(''); setAppliedQuery('') }}>Clear search ×</button></div>}
    {locationState === 'unavailable' && <p className="location-fallback" role="status">Location access is unavailable. You can still search by neighborhood or borough.</p>}
    <div className="network-source"><strong>Food mutual aid and community fridges</strong><span>{resources.length} curated resources · {resourceSource} · Not yet onboarded as NeedYield partners.</span></div>
    <FoodMap locations={filtered} resources={filteredResources} userLocation={userLocation} />
    <div className="results-heading"><strong>{filtered.length} {filtered.length === 1 ? 'location' : 'locations'}</strong><span>Inventory updates when a reservation is made</span></div>
    {filtered.length ? <div className="location-grid">{filtered.map((location) => <LocationCard key={location.id} location={location} />)}</div> : <div className="empty-state"><span>🥬</span><h2>No food matched “{normalizeSearch(appliedQuery)}”</h2><p>Your search worked, but that item is not currently available. Check another spelling, try a nearby borough, or clear the filters.</p><button className="text-button" onClick={() => { setQuery(''); setAppliedQuery(''); setBorough('All boroughs') }}>Clear filters</button></div>}
  </div>
}
