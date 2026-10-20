import { Link } from 'react-router-dom'
import { Code2, MessageSquare, ShieldAlert } from 'lucide-react'
import { Faq, PageHeader, Prose, Section, useTitle } from '@/components/bits'
import { Button } from '@/components/ui/button'
import { FAQ, PRIVACY, REPO, STATUS, TERMS } from '@/content'

export function FaqPage() {
  useTitle('FAQ')
  return (
    <>
      <PageHeader eyebrow="FAQ" title="Frequently asked questions" lead="Straight answers, including the ones about what the software cannot do yet." />
      <Section><Faq items={FAQ} /></Section>
      <Section tone="muted">
        <p className="text-center">Something not answered? <Link to="/contact" className="underline">Ask on GitHub</Link>.</p>
      </Section>
    </>
  )
}

export function About() {
  useTitle('About')
  return (
    <>
      <PageHeader eyebrow="About" title="Built so advocates can use AI without risking client confidentiality" />
      <Section title="Why it exists">
        <div className="text-muted-foreground grid max-w-3xl gap-4 text-lg leading-relaxed">
          <p>Indian cross-examination hinges on contradictions (s.148 Bharatiya Sakshya Adhiniyam) and material omissions (Explanation to s.181 BNSS) between a witness’s court testimony and earlier statements. Advocates find them by reading hundreds of pages by hand, and an omission cannot be searched for.</p>
          <p>Case files are privileged, so cloud AI puts client confidentiality at risk, and general chatbots invent quotes. Nyaya AI is the opposite design: it runs on your laptop, and a model’s output is checked by code before you see it.</p>
        </div>
      </Section>
      <Section tone="muted" title="What is built, and what is not" lead="A plain status, updated as the project moves.">
        <ul className="grid max-w-3xl gap-2">
          {STATUS.map((s) => (
            <li key={s.item} className="bg-card flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 rounded-xl border p-4 text-sm">
              <span>{s.item}</span>
              <span className="text-muted-foreground">{s.status}</span>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Principles">
        <ul className="grid gap-4 md:grid-cols-3">
          {[
            ['The model proposes, code verifies', 'Anything the AI says is checked against the document before you see it.'],
            ['You decide', 'Findings are drafts. The advocate confirms or dismisses each one.'],
            ['Local first', 'Nothing leaves the machine, and nothing is stored in the clear.'],
          ].map(([t, d]) => (
            <li key={t} className="bg-card rounded-2xl border p-5"><h3 className="font-semibold">{t}</h3><p className="text-muted-foreground mt-2 text-sm">{d}</p></li>
          ))}
        </ul>
        <p className="text-muted-foreground mt-8 text-sm">No real client data is used in testing. The test cases are fictional.</p>
      </Section>
    </>
  )
}

export function Contact() {
  useTitle('Contact')
  const cards = [
    { icon: MessageSquare, title: 'Questions and feedback', body: 'Ask a question, request a feature, or tell us a finding looked wrong.', href: `${REPO}/issues/new`, cta: 'Open an issue' },
    { icon: ShieldAlert, title: 'Report a vulnerability', body: 'Please use a private security advisory, not a public issue, and do not include real case data.', href: `${REPO}/security/advisories/new`, cta: 'Report privately' },
    { icon: Code2, title: 'Contribute', body: 'The code is MIT licensed. Pull requests, test cases and legal review of the event vocabulary are welcome.', href: REPO, cta: 'View the repository' },
  ]
  return (
    <>
      <PageHeader eyebrow="Contact" title="Get in touch" lead="The project lives on GitHub. Please never paste real case files or client details into an issue." />
      <Section>
        <ul className="grid gap-4 md:grid-cols-3">
          {cards.map((c) => (
            <li key={c.title} className="bg-card flex flex-col rounded-2xl border p-6">
              <c.icon className="mb-3 size-6" aria-hidden />
              <h2 className="text-lg font-semibold">{c.title}</h2>
              <p className="text-muted-foreground mt-2 flex-1 text-sm">{c.body}</p>
              <Button asChild variant="outline" className="mt-5 self-start"><a href={c.href} rel="noreferrer" target="_blank">{c.cta}</a></Button>
            </li>
          ))}
        </ul>
      </Section>
    </>
  )
}

export function Privacy() {
  useTitle('Privacy')
  return (<><PageHeader eyebrow="Legal" title="Privacy policy" /><Prose rows={PRIVACY as unknown as [string, string][]} /></>)
}

export function Terms() {
  useTitle('Terms')
  return (<><PageHeader eyebrow="Legal" title="Terms of use" /><Prose rows={TERMS as unknown as [string, string][]} /></>)
}

export function NotFound() {
  useTitle('Page not found')
  return (
    <section className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-muted-foreground text-sm font-medium tracking-wide uppercase">404</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-muted-foreground mt-3">That page does not exist. It may have moved.</p>
      <Button asChild className="mt-8"><Link to="/">Back to home</Link></Button>
    </section>
  )
}
