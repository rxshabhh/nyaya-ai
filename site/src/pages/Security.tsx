import { Link } from 'react-router-dom'
import { KeyRound, Lock, ServerOff, ShieldAlert } from 'lucide-react'
import SpotlightCard from '@/components/SpotlightCard'
import { PageHeader, Section, useTitle } from '@/components/bits'
import { Button } from '@/components/ui/button'

const CARDS = [
  { icon: ServerOff, title: 'Offline by design', body: 'No account, no cloud, no telemetry. The local model address must be this machine; anything else is refused, even if misconfigured.' },
  { icon: Lock, title: 'Encrypted at rest', body: 'Documents, document names and the findings database are encrypted with AES-256-GCM. There is no plaintext database file. Tampered or swapped files fail to decrypt.' },
  { icon: KeyRound, title: 'Your passphrase is the only key', body: 'A key derived with Argon2id (3 passes, 64 MiB, 4 lanes) locks a random per-case key. Changing the passphrase re-wraps one small key; no document is re-encrypted. Minimum 8 characters.' },
  { icon: ShieldAlert, title: 'Guarded local app', body: 'The app listens on 127.0.0.1 only. Each launch makes a one-time key, and Host and Origin checks stop other web pages in your browser from reaching it. The page ships with a strict content security policy.' },
]

const MODEL = [
  ['Protected', 'A lost or stolen laptop. A copied case folder or archive. Another person browsing your files.'],
  ['Also covered', 'Other tabs or websites in your browser trying to call the local app. Tampering with or swapping encrypted files.'],
  ['Not covered', 'Someone using your computer while a case is unlocked, malware running as you, or inspection of the running process’s memory. Python cannot guarantee keys are wiped from memory.'],
  ['Be aware', 'The case code name is stored unencrypted so the list can show it. Use a code, not a client’s name. A lost passphrase cannot be recovered.'],
]

export default function Security() {
  useTitle('Security')
  return (
    <>
      <PageHeader eyebrow="Security and privacy" title="Case files are privileged. The design assumes that." lead="Everything runs on your laptop and everything stored is encrypted. Here is exactly what that does and does not protect against." />
      <Section>
        <ul className="grid gap-4 sm:grid-cols-2">
          {CARDS.map((c) => (
            <li key={c.title}>
              <SpotlightCard theme="light" className="bg-card h-full rounded-2xl border p-6">
                <c.icon className="mb-3 size-6" aria-hidden />
                <h2 className="text-lg font-semibold">{c.title}</h2>
                <p className="text-muted-foreground mt-2">{c.body}</p>
              </SpotlightCard>
            </li>
          ))}
        </ul>
      </Section>
      <Section tone="muted" title="Threat model in plain words">
        <dl className="grid max-w-3xl gap-3">
          {MODEL.map(([t, d]) => (
            <div key={t} className="bg-card rounded-xl border p-5">
              <dt className="font-semibold">{t}</dt>
              <dd className="text-muted-foreground mt-1">{d}</dd>
            </div>
          ))}
        </dl>
        <p className="text-muted-foreground mt-8 max-w-3xl text-sm">
          The code is open source, so you or your IT adviser can read it. To report a vulnerability, use the project’s GitHub security advisories rather than a public issue.
        </p>
        <div className="mt-6 flex gap-3">
          <Button asChild variant="outline"><Link to="/privacy">Privacy policy</Link></Button>
          <Button asChild variant="outline"><Link to="/contact">Contact</Link></Button>
        </div>
      </Section>
    </>
  )
}
