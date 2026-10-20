import { useState } from 'react'
import { Check, ChevronDown, Printer, RotateCcw, X } from 'lucide-react'
import CountUp from '@/components/CountUp'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { api, cite, DOCTYPES, eventName, type Claim, type DocInfo, type Finding, type Results } from '@/lib/api'

type State = Finding['state']
const FILTERS = [['open', 'To review'], ['confirmed', 'Confirmed'], ['dismissed', 'Dismissed'], ['all', 'All']] as const
type Filter = (typeof FILTERS)[number][0]

function Quote({ c, docs }: { c: Claim; docs: Map<string, DocInfo> }) {
  const d = docs.get(c.doc)
  return (
    <figure className="grid gap-1.5">
      <figcaption className="text-muted-foreground text-xs">
        {d ? `${DOCTYPES[d.doctype]}, ${d.date}` : 'Document removed'} · <span className="font-mono">{cite(c)}</span>
      </figcaption>
      <blockquote className="border-l-2 pl-3 text-sm leading-relaxed">“{c.exact_quote}”</blockquote>
    </figure>
  )
}

function FindingCard({ f, docs, onState }: { f: Finding; docs: Map<string, DocInfo>; onState: (s: State) => void }) {
  const decided = f.state !== 'open'
  let body
  if (f.kind === 'contradiction') {
    // earlier statement on the left, court testimony on the right
    const [x, y] = docs.get(f.a.doc)?.kind === 'court' ? [f.b, f.a] : [f.a, f.b]
    body = (
      <>
        <CardDescription>{f.witness} · {eventName(x)} · differs on {f.fields.join(', ')}</CardDescription>
        <CardContent className="grid gap-4 px-0">
          <div className="grid gap-4 md:grid-cols-2">
            <Quote c={x} docs={docs} />
            <Quote c={y} docs={docs} />
          </div>
          <table className="w-full max-w-lg text-sm">
            <tbody>
              {f.fields.map((k) => (
                <tr key={k} className="border-t">
                  <th scope="row" className="text-muted-foreground py-1 pr-4 text-left font-normal capitalize">{k}</th>
                  <td className="py-1 pr-4">{String(x[k as keyof Claim] ?? '—')}</td>
                  <td className="py-1">{String(y[k as keyof Claim] ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </>
    )
  } else {
    body = (
      <>
        <CardDescription>
          {f.witness} · {eventName(f.claim)} ·{' '}
          {f.omission === 'court_only' ? 'said first in court, not told to police' : 'told police, not repeated in court'}
        </CardDescription>
        <CardContent className="px-0"><Quote c={f.claim} docs={docs} /></CardContent>
      </>
    )
  }

  return (
    <Card className={decided ? 'opacity-80' : ''}>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {f.kind === 'contradiction' ? 'Contradiction' : 'Omission'}
          {f.kind === 'omission' && f.material && <Badge variant="destructive">Likely material</Badge>}
          {f.state === 'confirmed' && <Badge>Confirmed</Badge>}
          {f.state === 'dismissed' && <Badge variant="outline">Dismissed</Badge>}
          {f.stale && <Badge variant="outline">Not in latest analysis</Badge>}
        </CardTitle>
        {body}
        <CardAction className="flex gap-1 print:hidden">
          {decided ? (
            <Button size="sm" variant="ghost" onClick={() => onState('open')}><RotateCcw /> Reopen</Button>
          ) : (
            <>
              <Button size="sm" onClick={() => onState('confirmed')}><Check /> Confirm</Button>
              <Button size="sm" variant="outline" onClick={() => onState('dismissed')}><X /> Dismiss</Button>
            </>
          )}
        </CardAction>
      </CardHeader>
    </Card>
  )
}

export function Findings(props: {
  base: string
  label: string
  docs: DocInfo[]
  results: Results | null
  onChange: (r: Results) => void
  onError: (e: unknown) => void
}) {
  const { results } = props
  const [filter, setFilter] = useState<Filter>('open')
  if (!results) return <p className="text-muted-foreground text-sm">Loading…</p>

  const docs = new Map(props.docs.map((d) => [d.name, d]))
  const live = results.findings.filter((f) => !f.stale)
  const stale = results.findings.filter((f) => f.stale)
  const shown = live.filter((f) => filter === 'all' || f.state === filter)
  const count = (s: Filter) => live.filter((f) => s === 'all' || f.state === s).length

  async function setState(f: Finding, state: State) {
    const prev = results!
    props.onChange({ ...prev, findings: prev.findings.map((g) => (g.key === f.key ? { ...g, state } : g)) })
    try {
      await api(`${props.base}/findings/${f.key}`, { method: 'PUT', json: { state } })
    } catch (e) {
      props.onChange(prev)
      props.onError(e)
    }
  }

  const tiles = [
    ['Contradictions', results.counts.contradictions],
    ['Omissions', results.counts.omissions],
    ['Verified claims', results.counts.verified],
    ['Rejected claims', results.counts.rejected],
  ] as const

  return (
    <div className="grid gap-6">
      <h2 className="hidden text-xl font-semibold print:block">{props.label}: findings</h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tiles.map(([k, v]) => (
          <div key={k} className="rounded-xl border p-4">
            <dt className="text-muted-foreground text-xs">{k}</dt>
            <dd className="text-2xl font-semibold tabular-nums"><CountUp to={v} duration={0.6} /></dd>
          </div>
        ))}
      </dl>

      {live.length === 0 && stale.length === 0 ? (
        <p className="text-muted-foreground text-sm">No findings yet. Add each witness's earlier statement and court testimony, then run the analysis.</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
            <div role="group" aria-label="Filter findings" className="flex flex-wrap gap-1">
              {FILTERS.map(([k, v]) => (
                <Button key={k} size="sm" variant={filter === k ? 'default' : 'outline'} aria-pressed={filter === k} onClick={() => setFilter(k)}>
                  {v} ({count(k)})
                </Button>
              ))}
            </div>
            <Button size="sm" variant="ghost" onClick={() => window.print()}><Printer /> Print or save as PDF</Button>
          </div>

          <div className="grid gap-3">
            {shown.length === 0 && <p className="text-muted-foreground text-sm">Nothing here.</p>}
            {shown.map((f) => <FindingCard key={f.key} f={f} docs={docs} onState={(s) => setState(f, s)} />)}
          </div>

          {stale.length > 0 && (
            <Collapsible className="print:hidden">
              <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-sm hover:underline">
                <ChevronDown className="size-4" aria-hidden /> {stale.length} earlier finding(s) not produced by the latest analysis
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3 grid gap-3">
                {stale.map((f) => <FindingCard key={f.key} f={f} docs={docs} onState={(s) => setState(f, s)} />)}
              </CollapsibleContent>
            </Collapsible>
          )}
        </>
      )}
    </div>
  )
}

export function Rejected({ claims }: { claims: Claim[] }) {
  return (
    <div className="grid gap-3">
      <p className="text-muted-foreground text-sm">
        The verification gate threw these out because a quote or a detail was not found in the cited paragraph.
        They are never used for findings.
      </p>
      {claims.length === 0 && <p className="text-sm">No rejected claims.</p>}
      {claims.map((c, i) => (
        <Card key={i}>
          <CardHeader>
            <CardDescription className="font-mono text-xs">{cite(c)} · {eventName(c)}</CardDescription>
            <blockquote className="border-l-2 pl-3 text-sm">“{c.exact_quote}”</blockquote>
            <p className="text-destructive text-sm">{c.reason}</p>
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}
