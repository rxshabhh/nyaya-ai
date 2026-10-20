import { Link } from 'react-router-dom'
import SpotlightCard from '@/components/SpotlightCard'
import { PageHeader, Section, useTitle } from '@/components/bits'
import { Button } from '@/components/ui/button'
import { FEATURES } from '@/content'

const LIMITS = [
  'English only. Indian languages are not supported yet.',
  'Text, digital PDF and Word only. Scanned PDFs are refused with a message naming the pages; there is no OCR in version 1.',
  'Claim extraction with a live local model has not yet been measured on real case files.',
  'Materiality ranking is a keyword heuristic. You decide what is material.',
]

export default function Features() {
  useTitle('Features')
  return (
    <>
      <PageHeader eyebrow="Features" title="Everything a cross-examination file needs, nothing that leaves the laptop" lead="Built around one rule: the AI proposes, code verifies, and you decide." />
      <Section>
        <ul className="grid gap-4 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <li key={f.title}>
              <SpotlightCard theme="light" className="bg-card h-full rounded-2xl border p-6">
                <h2 className="text-lg font-semibold">{f.title}</h2>
                <p className="text-muted-foreground mt-2">{f.body}</p>
              </SpotlightCard>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="muted" title="See it working">
        <div className="grid gap-6 lg:grid-cols-2">
          <figure className="bg-card overflow-hidden rounded-2xl border">
            <img src="/img/app-findings.png" alt="Findings screen with contradictions and omissions" className="w-full" loading="lazy" />
            <figcaption className="text-muted-foreground border-t px-4 py-2 text-sm">Findings: side-by-side quotes with page and paragraph, Confirm or Dismiss.</figcaption>
          </figure>
          <figure className="bg-card overflow-hidden rounded-2xl border">
            <img src="/img/app-documents.png" alt="Documents screen grouped by witness with an analysis panel" className="w-full" loading="lazy" />
            <figcaption className="text-muted-foreground border-t px-4 py-2 text-sm">Documents grouped by witness, with analysis progress.</figcaption>
          </figure>
        </div>
      </Section>

      <Section title="Honest limits in version 1" lead="So you know what to check yourself.">
        <ul className="grid max-w-3xl gap-3">
          {LIMITS.map((l) => <li key={l} className="bg-card rounded-xl border p-4 text-sm">{l}</li>)}
        </ul>
        <div className="mt-8 flex gap-3">
          <Button asChild><Link to="/get-started">Get started</Link></Button>
          <Button asChild variant="outline"><Link to="/about">See the roadmap</Link></Button>
        </div>
      </Section>
    </>
  )
}
