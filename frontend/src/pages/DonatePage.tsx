import { useEffect, useMemo, useState } from 'react'
import { analyzeProduce, confirmDonation, getDonationDestinations, matchDistribution, type Allocation, type MatchInput, type MatchResult } from '../services/api'
import { useApp } from '../context/AppContext'
import type { FoodLocation } from '../types'

type HarvestItem = { name: string; quantity: number; confidence: number }

export function DonatePage() {
  const { locations, refreshLocations, backendConnected } = useApp()
  const [step, setStep] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [items, setItems] = useState<HarvestItem[]>([])
  const [analysisSource, setAnalysisSource] = useState('')
  const [donationDestinations, setDonationDestinations] = useState<FoodLocation[]>([])
  const [preferred, setPreferred] = useState('')
  const [radius, setRadius] = useState(15)
  const [match, setMatch] = useState<MatchResult | null>(null)
  const [allocations, setAllocations] = useState<Allocation[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const totalAllocated = useMemo(() => allocations.reduce((sum, item) => sum + item.quantity, 0), [allocations])

  useEffect(() => {
    getDonationDestinations()
      .then((destinations) => {
        setDonationDestinations(destinations)
        setPreferred((current) => current || destinations[0]?.id || '')
      })
      .catch(() => {
        const eligible = locations.filter((location) => location.verifiedPartner && location.participating && location.acceptsSaturday && (location.acceptedCategories?.length || 0) > 0)
        setDonationDestinations(eligible)
        setPreferred((current) => current || eligible[0]?.id || '')
      })
  }, [locations])

  function chooseFile(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    setError('')
    if (!selected) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) || selected.size > 8 * 1024 * 1024) {
      setError('Choose a JPEG, PNG, or WEBP image no larger than 8 MB.')
      return
    }
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
  }

  async function runAnalysis() {
    if (!file) return
    setBusy(true); setError('')
    try {
      const result = await analyzeProduce(file)
      const analyzedItems = result.items.map((item) => ({ name: item.name, quantity: item.estimated_quantity, confidence: item.confidence }))
      setItems(analyzedItems.length ? analyzedItems : [{ name: '', quantity: 1, confidence: 0 }])
      setAnalysisSource(result.source)
      setStep(2)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Analysis failed. Enter your harvest manually.'); setItems([{ name: '', quantity: 1, confidence: 0 }]); setStep(2) }
    finally { setBusy(false) }
  }

  async function runMatch() {
    setBusy(true); setError('')
    const input: MatchInput = { gardener_latitude: 40.79, gardener_longitude: -73.95, preferred_location_id: preferred, preferred_radius_miles: radius, items: items.filter((item) => item.name && item.quantity > 0).map((item) => ({ name: item.name, quantity: item.quantity, unit: 'count' })) }
    try {
      const result = await matchDistribution(input)
      setMatch(result); setAllocations([...result.preferred_allocations, ...result.recommended_allocations]); setStep(3)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Matching is temporarily unavailable.') }
    finally { setBusy(false) }
  }

  async function confirm() {
    if (!match) return
    setBusy(true); setError('')
    const input: MatchInput = { gardener_latitude: 40.79, gardener_longitude: -73.95, preferred_location_id: preferred, preferred_radius_miles: radius, items: items.map((item) => ({ name: item.name, quantity: item.quantity, unit: 'count' })) }
    try { await confirmDonation(input, allocations.filter((item) => item.quantity > 0)); await refreshLocations(); setConfirmed(true); setStep(4) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not confirm this plan.') }
    finally { setBusy(false) }
  }

  return <div className="page container donate-page">
    <header className="page-header"><span className="kicker">GARDENER WORKFLOW</span><h1>Give your harvest a home.</h1><p>Confirm what you grew, prioritize your usual organization, then route remaining surplus where it can help.</p></header>
    <div className="workflow-progress" aria-label={`Step ${step} of 4`}>{['Photo', 'Confirm harvest', 'Review plan', 'Published'].map((label, index) => <div className={step >= index + 1 ? 'active' : ''} key={label}><span>{index + 1}</span>{label}</div>)}</div>
    {!backendConnected && <div className="notice warning"><span>!</span><p><strong>Backend not connected.</strong> Start the FastAPI server to analyze and match donations.</p></div>}
    {error && <p className="workflow-error" role="alert">{error}</p>}
    {step === 1 && <section className="workflow-card upload-step"><div><span className="kicker">STEP 1</span><h2>Photograph your harvest</h2><p>Upload a clear photo. NeedYield will estimate the visible produce and quantities.</p><label className="upload-box"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseFile} /><span>Choose produce photo</span><small>JPEG, PNG, or WEBP · 8 MB maximum</small></label>{file && <button className="button button-dark" onClick={runAnalysis} disabled={busy}>{busy ? 'Analyzing your harvest…' : 'Analyze harvest →'}</button>}</div>{preview ? <img src={preview} alt="Harvest selected for analysis" /> : <div className="photo-placeholder">◎<span>Your harvest photo</span></div>}</section>}
    {step === 2 && <section className="workflow-card"><span className="kicker">STEP 2</span><h2>{analysisSource === 'mock_fallback' ? 'Enter your harvest' : 'We found:'}</h2><p className={`ai-note ${analysisSource === 'mock_fallback' ? 'warning' : ''}`}>{analysisSource === 'mock_fallback' ? <strong>We couldn't confidently analyze this photo. Enter your produce manually.</strong> : 'AI estimates can be imperfect. Please confirm your harvest before continuing.'}</p><div className="harvest-editor">{items.map((item, index) => <div className="harvest-row" key={index}><label>Produce<input value={item.name} onChange={(event) => setItems((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, name: event.target.value } : row))} /></label><label>Quantity<input type="number" min="1" value={item.quantity} onChange={(event) => setItems((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, quantity: Number(event.target.value) } : row))} /></label>{analysisSource !== 'mock_fallback' && <span>{Math.round(item.confidence * 100)}% confidence</span>}</div>)}</div><button className="text-button" onClick={() => setItems((current) => [...current, { name: '', quantity: 1, confidence: 0 }])}>+ Add another item</button><div className="preference-grid"><label>Preferred donation destination<select value={preferred} onChange={(event) => setPreferred(event.target.value)} disabled={!donationDestinations.length}>{donationDestinations.map((location) => <option value={location.id} key={location.id}>{location.name} · accepts {location.acceptedCategories?.join(', ')}</option>)}</select><small>Only verified partners currently accepting produce appear here.</small></label><label>Redistribution radius<select value={radius} onChange={(event) => setRadius(Number(event.target.value))}><option value="5">5 miles</option><option value="10">10 miles</option><option value="15">15 miles</option><option value="25">25 miles</option></select></label></div>{!donationDestinations.length && <p className="workflow-error" role="status">No verified donation destinations are accepting produce right now.</p>}<button className="button button-primary" onClick={runMatch} disabled={busy || !preferred || !items.some((item) => item.name && item.quantity > 0)}>{busy ? 'Building your plan…' : 'Find destinations →'}</button></section>}
    {step === 3 && match && <section className="workflow-card"><span className="kicker">STEP 3</span><h2>Your distribution plan</h2><p>Your preferred organization is served up to its stated need. Remaining produce is ranked deterministically by community need, produce need, distance, inventory, and Saturday hours.</p><div className="allocation-list">{allocations.map((allocation, index) => <article className={allocation.preferred ? 'preferred-allocation' : ''} key={`${allocation.location_id}-${allocation.produce}`}><div><span className="demo-badge">{allocation.preferred ? 'Preferred' : `Score ${Math.round(allocation.score * 100)}`}</span><h3>{allocation.location_name}</h3><strong>{allocation.produce}</strong><ul>{allocation.reasons.slice(0, 4).map((reason) => <li key={reason}>{reason}</li>)}</ul></div><label>Suggested quantity<input type="number" min="0" value={allocation.quantity} onChange={(event) => setAllocations((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, quantity: Number(event.target.value) } : row))} /></label></article>)}</div>{match.surplus_alert && <div className="surplus-alert"><strong>Surplus alert</strong><p>{Object.entries(match.remaining_surplus).filter(([, value]) => value > 0).map(([name, value]) => `${value} ${name}`).join(', ')} still need a home. Nothing will be redirected without your confirmation.</p></div>}<p className="data-source">Community-need signal: {match.data_source}</p><div className="plan-footer"><strong>{totalAllocated} items allocated</strong><button className="button button-dark" onClick={confirm} disabled={busy}>{busy ? 'Publishing…' : 'Confirm & publish inventory'}</button></div></section>}
    {step === 4 && confirmed && <section className="workflow-card success-step"><span>✓</span><h2>Your harvest is published.</h2><p>The confirmed allocations have been added to resident-facing inventory. Neighbors can reserve them now.</p><a className="button button-primary" href="/find-food">View fresh food inventory →</a></section>}
  </div>
}
