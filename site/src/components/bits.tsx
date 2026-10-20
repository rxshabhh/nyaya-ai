import type { ReactNode } from 'react'
import { useEffect } from 'react'
import FadeContent from '@/components/FadeContent'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

export function useTitle(title: string) {
  useEffect(() => {
    document.title = title === 'Nyaya AI' ? 'Nyaya AI: offline cross-examination prep for advocates' : `${title} · Nyaya AI`
  }, [title])
}

export function PageHeader({ eyebrow, title, lead }: { eyebrow: string; title: string; lead?: ReactNode }) {
  return (
    <section className="border-b">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:py-20">
        <FadeContent blur duration={0.7} trigger="mount">
          <p className="text-muted-foreground mb-3 text-sm font-medium tracking-wide uppercase">{eyebrow}</p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">{title}</h1>
          {lead && <p className="text-muted-foreground mt-5 max-w-2xl text-lg text-pretty">{lead}</p>}
        </FadeContent>
      </div>
    </section>
  )
}

export function Section({ title, lead, children, tone }: { title?: string; lead?: ReactNode; children: ReactNode; tone?: 'muted' }) {
  return (
    <section className={tone === 'muted' ? 'bg-muted/50 border-y' : ''}>
      <div className="mx-auto max-w-6xl px-4 py-14 sm:py-16">
        {title && (
          <div className="mb-10 max-w-2xl">
            <h2 className="text-3xl font-semibold tracking-tight text-balance">{title}</h2>
            {lead && <p className="text-muted-foreground mt-3 text-lg">{lead}</p>}
          </div>
        )}
        {children}
      </div>
    </section>
  )
}

export function Prose({ rows }: { rows: readonly (readonly [string, string])[] }) {
  return (
    <div className="mx-auto grid max-w-3xl gap-8 px-4 py-14">
      {rows.map(([h, p]) => (
        <section key={h}>
          <h2 className="text-xl font-semibold">{h}</h2>
          <p className="text-muted-foreground mt-2 leading-relaxed">{p}</p>
        </section>
      ))}
    </div>
  )
}

export function Faq({ items }: { items: readonly { q: string; a: string }[] }) {
  return (
    <Accordion type="single" collapsible className="mx-auto w-full max-w-3xl">
      {items.map((f, i) => (
        <AccordionItem key={f.q} value={`q${i}`}>
          <AccordionTrigger className="text-left text-base">{f.q}</AccordionTrigger>
          <AccordionContent className="text-muted-foreground text-base leading-relaxed">{f.a}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}

export function Code({ children }: { children: string }) {
  return (
    <pre className="bg-primary text-primary-foreground overflow-x-auto rounded-xl p-4 text-sm leading-relaxed">
      <code>{children}</code>
    </pre>
  )
}
