import { seedLocations } from '../data/locations'
import type { FoodLocation, Reservation } from '../types'

const LOCATIONS_KEY = 'needyield.locations.v2'
const RESERVATIONS_KEY = 'needyield.reservations.v2'

function cloneSeedLocations() {
  return structuredClone(seedLocations)
}

export function loadLocations(): FoodLocation[] {
  try {
    const stored = localStorage.getItem(LOCATIONS_KEY)
    return stored ? JSON.parse(stored) : cloneSeedLocations()
  } catch {
    return cloneSeedLocations()
  }
}

export function saveLocations(locations: FoodLocation[]) {
  localStorage.setItem(LOCATIONS_KEY, JSON.stringify(locations))
}

export function loadReservations(): Reservation[] {
  try {
    return JSON.parse(localStorage.getItem(RESERVATIONS_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveReservations(reservations: Reservation[]) {
  localStorage.setItem(RESERVATIONS_KEY, JSON.stringify(reservations))
}
