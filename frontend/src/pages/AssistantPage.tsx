import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { queryRag, type RagResult } from '../services/api'

const prompts = [
  'Where can I find tomatoes near East Harlem?',
  "I need vegetables after 5 PM and don't have a car.",
  'Where can I find fresh produce this Saturday?',
]

function inlineMarkdown(text: string): ReactNode[] {
  return text.split(/(\*\*.*?\*\*)/g).filter(Boolean).map((part, index) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : <span key={index}>{part.replace(/\*/g, '')}</span>,
  )
}

function GroundedAnswer({ answer }: { answer: string }) {
  return <div className="answer-content">{answer.split('\n').map((rawLine, index) => {
    const line = rawLine.trim()
    if (!line) return <div className="answer-space" key={index} />
    if (line === '---') return <hr key={index} />
    if (line.startsWith('### ')) return <h3 key={index}>{inlineMarkdown(line.slice(4))}</h3>
    if (line.startsWith('## ')) return <h3 key={index}>{inlineMarkdown(line.slice(3))}</h3>
    if (/^[-*]\s/.test(line)) return <div className={`answer-bullet ${rawLine.startsWith('  ') ? 'nested' : ''}`} key={index}><span aria-hidden="true">•</span><p>{inlineMarkdown(line.slice(2))}</p></div>
    return <p key={index}>{inlineMarkdown(line)}</p>
  })}</div>
}

export function AssistantPage() {
  const [query, setQuery] = useState(''); const [result, setResult] = useState<RagResult | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState('')
  const submit = async (event?: FormEvent) => { event?.preventDefault(); if (query.trim().length < 3) return; setLoading(true); setError(''); try { setResult(await queryRag({ query: query.trim() })) } catch { setResult(null); setError("I couldn't run the AI resource search right now, but you can still browse currently available food below.") } finally { setLoading(false) } }
  return <div className="page assistant-page"><div className="container"><div className="assistant-hero"><span className="kicker">GROUNDED FOOD-ACCESS ASSISTANT</span><h1>Ask what you need.<br /><em>Find what’s available.</em></h1><p>NeedYield searches resource records semantically, then checks current inventory and hours before recommending a destination.</p><form className="assistant-form" onSubmit={submit}><label htmlFor="resource-question" className="sr-only">Ask about food resources</label><textarea id="resource-question" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="I need vegetables after work and don’t have a car. Where should I go?" minLength={3} maxLength={500} /><button className="button button-primary" disabled={loading || query.trim().length < 3}>{loading ? 'Searching…' : 'Find resources →'}</button></form><div className="prompt-chips" aria-label="Example questions">{prompts.map((prompt) => <button key={prompt} onClick={() => setQuery(prompt)}>{prompt}</button>)}</div><p className="grounded-label"><span>✦</span> Grounded in NeedYield inventory + NYC resource context</p></div>
      {error && <section className="assistant-results"><div className="workflow-error" role="alert">{error}</div><Link className="button button-dark" to="/find-food">Browse Find Food</Link></section>}
      {result && <section className="assistant-results" aria-live="polite"><div className="answer-card"><div className="answer-topline"><span>NEEDYIELD ANSWER</span><small>{result.retrieved_count} records retrieved</small></div><GroundedAnswer answer={result.answer} />{result.fallback && <small className="fallback-label">AI provider fallback active · recommendations still use current structured inventory.</small>}</div>
        <div className="recommendation-heading"><div><span className="kicker">VERIFIED CURRENT OPTIONS</span><h2>Where your food is</h2></div><Link to="/find-food">View on map →</Link></div>
        <div className="assistant-recommendations">{result.recommendations.map((item, index) => <article key={item.resource_id}><div className="recommendation-number">0{index + 1}</div><div><span className="demo-badge">DEMO LOCATION</span><h3>{item.name}</h3><p>{item.neighborhood}, {item.borough} · {item.hours}</p>{item.distance_miles != null && <p>{item.distance_miles} miles away</p>}<div className="assistant-inventory">{Object.entries(item.available_inventory).map(([food, quantity]) => <span key={food}><strong>{quantity}</strong> {food}</span>)}</div><ul>{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div></article>)}</div>
        <details className="source-panel"><summary>Sources and retrieval details</summary><p>Semantic retrieval: <strong>{result.retrieval_mode}</strong> · Generation: <strong>{result.generation_mode}</strong></p>{result.sources.map((source) => <div key={source.resource_id}><strong>{source.name}</strong><span>{source.source}</span>{source.source_url && <a href={source.source_url} target="_blank" rel="noreferrer">NYC source ↗</a>}</div>)}</details>
      </section>}
    </div></div>
}
