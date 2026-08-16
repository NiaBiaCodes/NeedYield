import { useEffect } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import type { FoodLocation, PublicResource } from '../types'
import { calculateDistanceMiles, directionsUrl } from '../utils/distance'
import 'leaflet/dist/leaflet.css'

type Coordinates = { latitude: number; longitude: number }

const foodMarker = L.divIcon({
  className: 'food-map-marker',
  html: '<span aria-hidden="true">NY</span>',
  iconSize: [38, 38],
  iconAnchor: [19, 38],
  popupAnchor: [0, -35],
})

const userMarker = L.divIcon({
  className: 'user-map-marker',
  html: '<span aria-hidden="true"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

const organizationMarker = L.divIcon({ className: 'organization-map-marker', html: '<span aria-hidden="true">🤝</span>', iconSize: [34, 34], iconAnchor: [17, 34], popupAnchor: [0, -31] })

function FitLocations({ locations, userLocation }: { locations: FoodLocation[]; userLocation: Coordinates | null }) {
  const map = useMap()
  useEffect(() => {
    const points = locations.map((location) => L.latLng(location.latitude, location.longitude))
    if (userLocation) points.push(L.latLng(userLocation.latitude, userLocation.longitude))
    if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [35, 35], maxZoom: 13 })
  }, [locations, userLocation, map])
  return null
}

function focusCard(id: string) {
  document.getElementById(`location-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

export function FoodMap({ locations, resources = [], userLocation }: { locations: FoodLocation[]; resources?: PublicResource[]; userLocation: Coordinates | null }) {
  return <section className="food-map-shell" aria-labelledby="food-map-title">
    <div className="map-heading"><div><span className="kicker">FOOD RESCUE NETWORK</span><h2 id="food-map-title">Fresh food and community resources</h2></div><p>{userLocation ? 'Distances are calculated from your current location.' : 'Participating locations and potential resources are clearly separated.'}</p></div>
    <div className="map-legend" aria-label="Map legend"><span><i className="legend-food">NY</i> Available produce</span><span><i className="legend-organization">🤝</i> Food mutual aid / community fridge</span></div>
    <MapContainer center={[40.76, -73.93]} zoom={11} scrollWheelZoom={false} className="food-map" aria-label="Map of participating demo food locations">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitLocations locations={locations} userLocation={userLocation} />
      {userLocation && <Marker position={[userLocation.latitude, userLocation.longitude]} icon={userMarker}><Popup><strong>Your approximate location</strong></Popup></Marker>}
      {locations.map((location) => {
        const available = location.inventory.filter((item) => item.quantity > 0)
        const distance = userLocation ? calculateDistanceMiles(userLocation.latitude, userLocation.longitude, location.latitude, location.longitude) : null
        return <Marker key={location.id} position={[location.latitude, location.longitude]} icon={foodMarker} title={location.name}>
          <Popup><div className="map-popup">
            <span className="demo-badge">Demo location</span>
            <h3>{location.name}</h3><p className="popup-neighborhood">{location.neighborhood}</p>
            {distance !== null && <p><strong>{distance.toFixed(1)} miles away</strong></p>}
            <p>Pickup: {location.openingTime}–{location.closingTime}</p>
            <ul>{available.slice(0, 4).map((item) => <li key={item.produce}><span>{item.produce}</span><strong>{item.quantity}</strong></li>)}</ul>
            <div className="popup-actions"><button type="button" onClick={() => focusCard(location.id)}>View & reserve</button><a href={directionsUrl(location.latitude, location.longitude)} target="_blank" rel="noreferrer">Get Directions ↗</a></div>
          </div></Popup>
        </Marker>
      })}
      {resources.map((resource) => <Marker key={resource.id} position={[resource.latitude, resource.longitude]} icon={organizationMarker} title={resource.name}><Popup><div className="map-popup resource-popup"><span className="resource-badge">Food donation resource</span><h3>{resource.name}</h3><p className="popup-neighborhood">{resource.neighborhood}</p><p>{resource.address}</p>{userLocation && <p><strong>{calculateDistanceMiles(userLocation.latitude, userLocation.longitude, resource.latitude, resource.longitude).toFixed(1)} miles away</strong></p>}<p className="match-signals"><strong>Resource type:</strong> {resource.resourceType.replaceAll('_', ' ')}<br /><strong>Food focus:</strong> {resource.matchedTerms.join(', ')}</p>{resource.operatingInformation && <p>{resource.operatingInformation}</p>}<p className="verification-warning"><strong>Not a NeedYield partner.</strong> {resource.acceptanceNote}</p><p className="resource-source">Source: {resource.source}</p>{resource.website && <a className="resource-website" href={resource.website} target="_blank" rel="noreferrer">Check current donation guidance ↗</a>}</div></Popup></Marker>)}
    </MapContainer>
  </section>
}
