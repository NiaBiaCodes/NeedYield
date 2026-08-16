const PRODUCE_ALIASES: Record<string, string> = {
  tomato: 'tomatoes', tomatos: 'tomatoes', tomatto: 'tomatoes', tomattoes: 'tomatoes', tomatoes: 'tomatoes',
  cucumber: 'cucumbers', cucumbers: 'cucumbers',
  pepper: 'peppers', peppers: 'peppers', 'bell pepper': 'peppers',
  carrot: 'carrots', carrots: 'carrots', herb: 'herbs', herbs: 'herbs',
  apple: 'apples', apples: 'apples', pear: 'pears', pears: 'pears',
  veggie: 'vegetables', veggies: 'vegetables', vegetable: 'vegetables', vegetables: 'vegetables',
}

export function normalizeSearch(value: string) {
  const normalized = value.toLowerCase().replace(/[^a-z0-9\s-]/g, ' ').replace(/\s+/g, ' ').trim()
  if (PRODUCE_ALIASES[normalized]) return PRODUCE_ALIASES[normalized]
  if (normalized.length >= 4 && !normalized.includes(' ')) {
    const produceNames = [...new Set(Object.values(PRODUCE_ALIASES))]
    const ranked = produceNames.map((name) => ({ name, distance: editDistance(normalized, name) })).sort((a, b) => a.distance - b.distance)
    const tolerance = normalized.length >= 6 ? 2 : 1
    if (ranked[0]?.distance <= tolerance) return ranked[0].name
  }
  return normalized
}

function editDistance(a: string, b: string) {
  const row = Array.from({ length: b.length + 1 }, (_, index) => index)
  for (let i = 1; i <= a.length; i += 1) {
    let previous = row[0]; row[0] = i
    for (let j = 1; j <= b.length; j += 1) {
      const held = row[j]
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, previous + (a[i - 1] === b[j - 1] ? 0 : 1))
      previous = held
    }
  }
  return row[b.length]
}

export function fuzzyMatches(query: string, candidate: string) {
  const needle = normalizeSearch(query); const target = normalizeSearch(candidate)
  if (!needle || target.includes(needle) || needle.includes(target)) return true
  const tolerance = needle.length >= 8 ? 2 : needle.length >= 4 ? 1 : 0
  return target.split(/\s+/).some((word) => editDistance(needle, word) <= tolerance)
}

export function foodCategory(produce: string): 'Fruits' | 'Vegetables' | 'Herbs' | 'Other produce' {
  const value = normalizeSearch(produce)
  if (['apples', 'pears', 'berries', 'oranges', 'peaches', 'plums', 'melon'].includes(value)) return 'Fruits'
  if (value === 'herbs' || ['basil', 'parsley', 'cilantro', 'mint'].includes(value)) return 'Herbs'
  if (['tomatoes', 'cucumbers', 'zucchini', 'kale', 'spinach', 'peppers', 'carrots', 'vegetables'].includes(value)) return 'Vegetables'
  return 'Other produce'
}
