import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { loadLocations, loadReservations, saveLocations, saveReservations } from '../services/storage'
import type { FoodLocation, Reservation } from '../types'
import { expireReservations, getTodayDeadline } from '../utils/reservations'
import * as api from '../services/api'
import { useAuth } from './AuthContext'

type ReservationInput = { locationId: string; produce: string; quantity: number }

type AppContextValue = {
  locations: FoodLocation[]
  reservations: Reservation[]
  reserveProduce: (input: ReservationInput) => Promise<Reservation>
  simulateExpiration: (reservationId: string) => Promise<void>
  refreshLocations: () => Promise<void>
  backendConnected: boolean
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [locations, setLocations] = useState<FoodLocation[]>(loadLocations)
  const [reservations, setReservations] = useState<Reservation[]>(loadReservations)
  const reservationsRef = useRef(reservations)
  const [backendConnected, setBackendConnected] = useState(false)
  const [backendChecked, setBackendChecked] = useState(false)

  const refreshLocations = async () => {
    try {
      const remoteLocations = await api.getLocations()
      setLocations(remoteLocations)
      setBackendConnected(true)
    } catch {
      setBackendConnected(false)
    } finally {
      setBackendChecked(true)
    }
  }

  const runExpiration = (targetId?: string) => {
    const { updated, released } = expireReservations(reservationsRef.current, new Date(), targetId)
    if (!released.length) return
    reservationsRef.current = updated
    setReservations(updated)
    setLocations((currentLocations) => currentLocations.map((location) => {
      const returns = released.filter((item) => item.locationId === location.id)
      if (!returns.length) return location
      return {
        ...location,
        inventory: location.inventory.map((item) => ({
          ...item,
          quantity: item.quantity + returns
            .filter((reservation) => reservation.produce === item.produce)
            .reduce((sum, reservation) => sum + reservation.quantity, 0),
        })),
      }
    }))
  }

  useEffect(() => {
    refreshLocations()
    api.getReservations().then((items) => {
      reservationsRef.current = items
      setReservations(items)
    }).catch(() => runExpiration())
    const interval = window.setInterval(() => {
      api.getReservations().then((items) => {
        reservationsRef.current = items
        setReservations(items)
        refreshLocations()
      }).catch(() => runExpiration())
    }, 60_000)
    return () => window.clearInterval(interval)
  }, [user?.id])

  useEffect(() => saveLocations(locations), [locations])
  useEffect(() => saveReservations(reservations), [reservations])

  const reserveProduce = async ({ locationId, produce, quantity }: ReservationInput) => {
    const location = locations.find((item) => item.id === locationId)
    const item = location?.inventory.find((inventoryItem) => inventoryItem.produce === produce)
    if (!location || !item || quantity < 1 || quantity > item.quantity) {
      throw new Error('That quantity is no longer available.')
    }
    if (backendConnected || !backendChecked) {
      try {
        const reservation = await api.createReservation({ locationId, produce, quantity })
        setBackendConnected(true)
        setBackendChecked(true)
        const nextReservations = [reservation, ...reservationsRef.current]
        reservationsRef.current = nextReservations
        setReservations(nextReservations)
        await refreshLocations()
        return reservation
      } catch (error) {
        if (error instanceof api.ApiRequestError) throw error
        setBackendConnected(false)
        setBackendChecked(true)
      }
    }
    const now = new Date()
    const reservation: Reservation = {
      id: crypto.randomUUID(),
      locationId,
      locationName: location.name,
      locationAddress: location.address,
      produce,
      quantity,
      reservedAt: now.toISOString(),
      expiresAt: getTodayDeadline(now).toISOString(),
      status: 'RESERVED',
    }
    setLocations((current) => current.map((candidate) => candidate.id === locationId
      ? { ...candidate, inventory: candidate.inventory.map((inventoryItem) => inventoryItem.produce === produce
        ? { ...inventoryItem, quantity: inventoryItem.quantity - quantity }
        : inventoryItem) }
      : candidate))
    const nextReservations = [reservation, ...reservationsRef.current]
    reservationsRef.current = nextReservations
    setReservations(nextReservations)
    return reservation
  }

  const value = useMemo(() => ({
    locations,
    reservations,
    reserveProduce,
    simulateExpiration: async (reservationId: string) => {
      if (backendConnected) {
        await api.expireReservation(reservationId)
        const items = await api.getReservations()
        reservationsRef.current = items
        setReservations(items)
        await refreshLocations()
      } else runExpiration(reservationId)
    },
    refreshLocations,
    backendConnected,
  }), [locations, reservations, backendConnected, backendChecked])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used inside AppProvider')
  return context
}
