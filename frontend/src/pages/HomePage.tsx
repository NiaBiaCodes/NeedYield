import { Link } from 'react-router-dom'

const steps = [
  ['01', 'Grow', 'Gardeners contribute surplus harvest.'],
  ['02', 'Match', 'NeedYield finds where produce can create the greatest impact.'],
  ['03', 'Reserve', 'Neighbors find and reserve fresh produce nearby.'],
  ['04', 'Rescue', 'Unclaimed produce is released again before it goes to waste.'],
]

export function HomePage() {
  return <>
    <section className="hero">
      <div className="hero-orb orb-one" /><div className="hero-orb orb-two" />
      <div className="container hero-content">
        <div className="eyebrow"><span />AI-powered produce redistribution for New York City</div>
        <h1>Fresh food shouldn't<br />go to <em>waste.</em></h1>
        <p>NeedYield uses AI and NYC data to connect surplus garden produce with the communities that need it — before it spoils.</p>
        <div className="hero-actions"><Link className="button button-primary" to="/find-food">Find Fresh Food <span>→</span></Link><Link className="button button-ghost" to="/donate">Donate Produce</Link></div>
        <p className="demo-disclaimer">Current locations and inventory are clearly labeled demo data.</p>
      </div>
      <div className="city-line" aria-hidden="true">NYC · GROWN HERE · SHARED HERE · NYC · GROWN HERE · SHARED HERE</div>
    </section>
    <section className="how-section container">
      <div className="section-heading"><div><span className="kicker">THE CYCLE</span><h2>How NeedYield works</h2></div><p>One connected loop keeps fresh food moving from surplus to need.</p></div>
      <div className="steps-grid">{steps.map(([number, title, copy]) => <article className="step-card" key={title}><span>{number}</span><div className="step-icon" aria-hidden="true">{title === 'Grow' ? '✦' : title === 'Match' ? '↗' : title === 'Reserve' ? '✓' : '↻'}</div><h3>{title}</h3><p>{copy}</p></article>)}</div>
    </section>
    <section className="mission-band"><div className="container"><p>The food exists.</p><p>The need exists.</p><strong>NeedYield connects them.</strong></div></section>
  </>
}

