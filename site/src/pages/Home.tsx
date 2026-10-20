import { Link } from 'react-router-dom'
import { ArrowRight, FileSearch, ScanSearch, ShieldCheck, WifiOff } from 'lucide-react'
import BlurText from '@/components/BlurText'
import CountUp from '@/components/CountUp'
import FadeContent from '@/components/FadeContent'
import GradientText from '@/components/GradientText'
import Magnet from '@/components/Magnet'
import ShinyText from '@/components/ShinyText'
import SpotlightCard from '@/components/SpotlightCard'
import { Faq, Section, useTitle } from '@/components/bits'
import { Button } from '@/components/ui/button'
import { AUDIENCE, FAQ, FEATURES, STEPS } from '@/content'

const PILLARS = [
  { icon: ScanSearch, title: 'Finds the conflicts', body: 'Contradictions and material omissions between court testimony and earlier statements.' },
  { icon: FileSearch, title: 'Cites every one', body: 'Both quotes, side by side, with document, page and paragraph.' },
  { icon: ShieldCheck, title: 'Never invents', body: 'Code checks each quote against the source before you see it.' },
  { icon: WifiOff, title: 'Stays on your laptop', body: 'Offline. Encrypted at rest. No account, no cloud, no telemetry.' },
]

function Hero() {
  return (
    <section className="relative overflow-hidden border-b">
      <div aria-hidden className="pointer-events-none absolute inset-0 [background:radial-gradient(60rem_30rem_at_70%_-10%,oklch(0.9_0.06_265/.5),transparent),radial-gradient(40rem_25rem_at_0%_20%,oklch(0.93_0.08_75/.45),transparent)]" />
      <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:py-24 lg:grid-cols-[1.05fr_1fr] lg:items-center">
        <div>
          <p className="bg-background/70 mb-5 inline-flex rounded-full border px-3 py-1 text-sm">
            <ShinyText text="Offline cross-examination prep for Indian advocates" speed={4} color="oklch(0.35 0.03 265)" shineColor="oklch(0.2 0.1 265)" />
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            <BlurText text="Find what a witness said, and what they left out." animateBy="words" delay={90} className="justify-start" />
          </h1>
          <p className="text-muted-foreground mt-6 max-w-xl text-lg text-pretty">
            Nyaya AI reads a case folder and flags where court testimony <GradientText colors={['#1e3a8a', '#b45309', '#1e3a8a']} animationSpeed={6} className="inline font-medium">contradicts or omits</GradientText> an earlier statement,
            under s.148 BSA and s.181 BNSS. Each finding cites its exact page. Nothing leaves your laptop.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Magnet magnetStrength={4} padding={40}>
              <Button asChild size="lg" className="h-11 px-5 text-base"><Link to="/get-started">Get started <ArrowRight /></Link></Button>
            </Magnet>
            <Button asChild variant="outline" size="lg" className="h-11 px-5 text-base"><Link to="/how-it-works">See how it works</Link></Button>
          </div>
          <p className="text-muted-foreground mt-4 text-sm">Free and open source. Runs on any Windows laptop; tuned for Snapdragon X.</p>
        </div>
        <FadeContent blur duration={0.9} delay={0.2} trigger="mount">
          <figure className="bg-card overflow-hidden rounded-2xl border shadow-xl">
            <img src="/img/app-findings.png" alt="Nyaya AI listing two contradictions and three omissions for a fictional robbery case, each with side-by-side quotes and Confirm and Dismiss buttons" width="1100" height="1310" className="w-full object-cover object-top" style={{ maxHeight: 520 }} />
            <figcaption className="text-muted-foreground border-t px-4 py-2 text-xs">The app on a fictional demo case.</figcaption>
          </figure>
        </FadeContent>
      </div>
    </section>
  )
}

export default function Home() {
  useTitle('Nyaya AI')
  return (
    <>
      <Hero />

      <Section>
        <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p) => (
            <li key={p.title}>
              <p.icon className="mb-3 size-6" aria-hidden />
              <h3 className="font-semibold">{p.title}</h3>
              <p className="text-muted-foreground mt-1 text-sm">{p.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="muted" title="Why this exists" lead="Cross-examination turns on two things advocates still find by hand.">
        <div className="grid gap-6 md:grid-cols-3">
          <SpotlightCard theme="light" className="bg-card rounded-2xl border p-6">
            <p className="text-5xl font-semibold tabular-nums"><CountUp to={54} suffix=" million" duration={1.4} /></p>
            <p className="text-muted-foreground mt-2 text-sm">cases pending across India’s courts at the end of 2025, as reported by the Government of India.</p>
          </SpotlightCard>
          <SpotlightCard theme="light" className="bg-card rounded-2xl border p-6">
            <h3 className="font-semibold">Contradictions and omissions</h3>
            <p className="text-muted-foreground mt-2 text-sm">A witness’s court testimony can be impeached with an earlier statement (s.148 Bharatiya Sakshya Adhiniyam). A material omission counts as a contradiction (Explanation to s.181 BNSS).</p>
          </SpotlightCard>
          <SpotlightCard theme="light" className="bg-card rounded-2xl border p-6">
            <h3 className="font-semibold">Files are privileged</h3>
            <p className="text-muted-foreground mt-2 text-sm">Uploading them to a cloud AI risks client confidentiality, and general chatbots invent quotes. Nyaya AI does neither.</p>
          </SpotlightCard>
        </div>
      </Section>

      <Section title="The model proposes. Code verifies." lead="A small language model only extracts claims. Nothing it says reaches you until the software has checked it against the document.">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="grid gap-4">
            {[
              ['The quote appears word for word in the cited paragraph', 'Stops invented quotes, and real quotes cited to the wrong page.'],
              ['Every date, time, place and amount appears inside the quote', 'Stops details the model made up or mixed up.'],
            ].map(([t, d]) => (
              <SpotlightCard key={t} theme="light" className="bg-card rounded-2xl border p-5">
                <p className="font-medium">{t}</p>
                <p className="text-muted-foreground mt-1 text-sm">{d}</p>
              </SpotlightCard>
            ))}
            <Button asChild variant="link" className="justify-start px-0"><Link to="/how-it-works">Read the full pipeline <ArrowRight /></Link></Button>
          </div>
          <figure className="bg-card overflow-hidden rounded-2xl border">
            <img src="/img/rejected-claims.png" alt="The Rejected claims list showing three planted false claims thrown out by the verification gate, each with its reason" className="w-full" loading="lazy" />
            <figcaption className="text-muted-foreground border-t px-4 py-2 text-xs">On the sample case the gate rejected all 3 planted false claims.</figcaption>
          </figure>
        </div>
      </Section>

      <Section tone="muted" title="What you get">
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.slice(0, 4).map((f) => (
            <li key={f.title}>
              <SpotlightCard theme="light" className="bg-card h-full rounded-2xl border p-5">
                <h3 className="font-semibold">{f.title}</h3>
                <p className="text-muted-foreground mt-2 text-sm">{f.body}</p>
              </SpotlightCard>
            </li>
          ))}
        </ul>
        <Button asChild variant="link" className="mt-4 px-0"><Link to="/features">All features <ArrowRight /></Link></Button>
      </Section>

      <Section title="Six steps from files to findings">
        <ol className="grid gap-x-10 gap-y-6 md:grid-cols-2">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-4">
              <span className="bg-primary text-primary-foreground grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold">{i + 1}</span>
              <div>
                <h3 className="font-semibold">{s.title}</h3>
                <p className="text-muted-foreground mt-1 text-sm">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section tone="muted" title="Who it is for">
        <div className="grid gap-4 md:grid-cols-3">
          {AUDIENCE.map((a) => (
            <div key={a.title} className="bg-card rounded-2xl border p-5">
              <h3 className="font-semibold">{a.title}</h3>
              <p className="text-muted-foreground mt-2 text-sm">{a.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Questions advocates ask first">
        <Faq items={FAQ.slice(0, 4)} />
        <p className="mt-6 text-center"><Button asChild variant="link"><Link to="/faq">More questions <ArrowRight /></Link></Button></p>
      </Section>

      <section className="bg-primary text-primary-foreground">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center">
          <h2 className="text-3xl font-semibold tracking-tight text-balance">Try it on the demo case in two minutes.</h2>
          <p className="mx-auto mt-3 max-w-xl opacity-80">The demo case is fictional and needs no AI model. See real contradictions, omissions and rejected claims first, then use your own files.</p>
          <Button asChild size="lg" variant="secondary" className="mt-8 h-11 px-6 text-base"><Link to="/get-started">Get started <ArrowRight /></Link></Button>
        </div>
      </section>
    </>
  )
}
