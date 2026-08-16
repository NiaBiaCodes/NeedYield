import { Link } from 'react-router-dom'

export function PlaceholderPage({ type }: { type: 'donate' | 'assistant' }) {
  const donate = type === 'donate'
  return <div className="page container"><div className="coming-soon"><span className="kicker">COMING IN THE NEXT PHASE</span><div className="coming-icon">{donate ? '◎' : '✦'}</div><h1>{donate ? 'Donate your harvest.' : 'Ask NeedYield.'}</h1><p>{donate ? 'The guided gardener workflow and AI produce recognition will arrive in Phase 2.' : 'The grounded food-access assistant will arrive after the core product and data pipeline are ready.'}</p><Link className="button button-primary" to="/find-food">Explore the Neighbor MVP</Link></div></div>
}

