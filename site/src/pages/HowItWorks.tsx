import { Link } from 'react-router-dom'
import SpotlightCard from '@/components/SpotlightCard'
import { PageHeader, Section, useTitle } from '@/components/bits'
import { Button } from '@/components/ui/button'
import { STEPS } from '@/content'

const STAGES = [
  ['Parse', 'CPU', 'Splits each document into (file, page, paragraph) so every quote has a citation.'],
  ['Extract', 'Local model', 'A small language model reads each paragraph and returns claims as JSON, one paragraph per call, so errors stay local and the citation is exact.'],
  ['Verify', 'CPU', 'Rejects any claim whose quote is not in the cited paragraph, or whose fields are not in the quote.'],
  ['Pair', 'Embedder', 'Matches claims about the same event, by event label first and by meaning when wording differs.'],
  ['Contradictions', 'CPU', 'Compares date, time, place and amount for the same witness and event across documents.'],
  ['Omissions', 'CPU', 'Finds events in one statement that are absent from the other, likely-material first.'],
  ['Review', 'You', 'Confirm or Dismiss each finding. Decisions are saved, encrypted, with the case.'],
]

const RULES = [
  ['Dates', 'Ranges must overlap to agree. “Intervening night of 12/13.03.2021” covers both days, so it matches “12.03.2021”.'],
  ['Times', '“At about” allows a 30 minute gap. Larger gaps are flagged.'],
  ['Places and amounts', 'Compared after normalising case and spacing. Rs. 5,000 against Rs. 8,000 is flagged.'],
  ['Who is compared', 'Only the same witness, across different documents. Two witnesses disagreeing is not flagged here.'],
]

export default function HowItWorks() {
  useTitle('How it works')
  return (
    <>
      <PageHeader eyebrow="How it works" title="From case folder to cited findings" lead="The language model is the only part that can be wrong, so it is the only part that is checked." />

      <Section title="The pipeline">
        <ol className="grid gap-3">
          {STAGES.map(([name, where, what], i) => (
            <li key={name}>
              <SpotlightCard theme="light" className="bg-card rounded-2xl border p-5">
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                  <span className="text-muted-foreground tabular-nums">{String(i + 1).padStart(2, '0')}</span>
                  <h2 className="text-lg font-semibold">{name}</h2>
                  <span className="bg-muted rounded-full px-2.5 py-0.5 text-xs">{where}</span>
                </div>
                <p className="text-muted-foreground mt-2 sm:ml-9">{what}</p>
              </SpotlightCard>
            </li>
          ))}
        </ol>
      </Section>

      <Section tone="muted" title="The verification gate" lead="This is what makes the output safe to read.">
        <div className="grid gap-6 lg:grid-cols-2">
          <ul className="grid content-start gap-3">
            <li className="bg-card rounded-xl border p-4"><strong>Quote check.</strong> The quote must appear word for word in the cited paragraph. This stops invented quotes and real quotes cited to the wrong page.</li>
            <li className="bg-card rounded-xl border p-4"><strong>Field check.</strong> Every date, time, place and amount must appear inside the quote. This stops made-up or mixed-up details.</li>
            <li className="bg-card rounded-xl border p-4"><strong>Citation by code.</strong> Document, page and paragraph are attached by the software, not read from the model.</li>
            <li className="bg-card rounded-xl border p-4"><strong>Nothing hidden.</strong> Rejected claims are listed with the reason, so you can see what was thrown out.</li>
          </ul>
          <figure className="bg-card overflow-hidden rounded-2xl border">
            <img src="/img/readme-contradiction.png" alt="A contradiction found by Nyaya AI: 11 pm at the shop against 9 pm at the house" className="w-full" loading="lazy" />
            <figcaption className="text-muted-foreground border-t px-4 py-2 text-sm">A contradiction: 11 pm at the shop against 9 pm at the house.</figcaption>
          </figure>
        </div>
      </Section>

      <Section title="What counts as a contradiction">
        <dl className="grid gap-4 sm:grid-cols-2">
          {RULES.map(([t, d]) => (
            <div key={t} className="bg-card rounded-xl border p-5">
              <dt className="font-semibold">{t}</dt>
              <dd className="text-muted-foreground mt-1 text-sm">{d}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section tone="muted" title="In your hands, step by step">
        <ol className="grid gap-x-10 gap-y-6 md:grid-cols-2">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-4">
              <span className="bg-primary text-primary-foreground grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold">{i + 1}</span>
              <div><h3 className="font-semibold">{s.title}</h3><p className="text-muted-foreground mt-1 text-sm">{s.body}</p></div>
            </li>
          ))}
        </ol>
        <Button asChild className="mt-8"><Link to="/get-started">Try the demo case</Link></Button>
      </Section>
    </>
  )
}
