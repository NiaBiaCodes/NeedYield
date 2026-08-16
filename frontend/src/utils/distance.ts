export function calculateDistanceMiles(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const earthRadiusMiles = 3958.8
  const toRadians = (degrees: number) => degrees * Math.PI / 180
  const latitudeDelta = toRadians(lat2 - lat1)
  const longitudeDelta = toRadians(lon2 - lon1)
  const value = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(longitudeDelta / 2) ** 2
  return earthRadiusMiles * 2 * Math.asin(Math.sqrt(value))
}

export function directionsUrl(latitude: number, longitude: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`
}

