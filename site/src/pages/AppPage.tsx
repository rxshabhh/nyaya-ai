import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Bot, Cloud, CloudOff, FolderOpen, LayoutGrid, ShieldCheck } from 'lucide-react'
import { CaseList } from '@/components/CaseList'
import { CaseView } from '@/components/CaseView'
import { Toaster } from '@/components/ui/sonner'
import { api, token, type CaseInfo } from '@/lib/api'

type Model = { backend: 'ollama' | 'gemini'; default_model: string; local: boolean }
type CloudState = { configured: boolean; signed_in: boolean; user: string | null }

const navItem = (active: boolean) =>
  `flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left font-medium transition-colors ${active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`

function Sidebar({ open, onHome, model, cloud }: { open: CaseInfo | null; onHome: (anchor?: string) => void; model: Model | null; cloud: CloudState | null }) {
  return (
    <aside className="grid content-start gap-5 lg:sticky lg:top-20">
      <div className="bg-card rounded-2xl border p-4">
        <p className="font-semibold">Nyaya AI workspace</p>
        <p className="text-muted-foreground mt-0.5 flex items-center gap-2 text-sm">
          <span className="size-2 rounded-full bg-emerald-500" aria-hidden /> Running on this laptop
        </p>
      </div>

      <nav aria-label="App" className="grid gap-1">
        <button type="button" className={navItem(!open)} onClick={() => onHome()}><LayoutGrid className="size-5" aria-hidden /> Cases</button>
        {open && <span className={navItem(true)}><FolderOpen className="size-5" aria-hidden /> <span className="truncate">{open.label}</span></span>}
        <button type="button" className={navItem(false)} onClick={() => onHome('cloud-sync')}><Cloud className="size-5" aria-hidden /> Cloud sync</button>
        <Link to="/docs" className={navItem(false)}><BookOpen className="size-5" aria-hidden /> Documentation</Link>
      </nav>

      <dl className="bg-card grid gap-4 rounded-2xl border p-4 text-sm">
        <div>
          <dt className="text-muted-foreground flex items-center gap-2"><Bot className="size-4" aria-hidden /> AI model</dt>
          <dd className="mt-0.5 font-medium">{model ? (model.local ? `Ollama, ${model.default_model}` : `Gemini, ${model.default_model}`) : '…'}</dd>
          {model && !model.local && <dd className="text-orange-700">Stand-in: fictional cases only</dd>}
        </div>
        <div>
          <dt className="text-muted-foreground flex items-center gap-2"><ShieldCheck className="size-4" aria-hidden /> Encryption</dt>
          <dd className="mt-0.5 font-medium">AES-256-GCM, key from passphrase</dd>
        </div>
        <div>
          <dt className="text-muted-foreground flex items-center gap-2">{cloud?.signed_in ? <Cloud className="size-4" aria-hidden /> : <CloudOff className="size-4" aria-hidden />} AWS locker</dt>
          <dd className="mt-0.5 font-medium break-all">{!cloud ? '…' : !cloud.configured ? 'Not set up' : cloud.signed_in ? cloud.user : 'Signed out'}</dd>
          {cloud?.configured && <dd className="text-muted-foreground">Mumbai, ap-south-1</dd>}
        </div>
      </dl>

      <p className="bg-primary text-primary-foreground rounded-2xl p-4 text-sm leading-relaxed">
        Every finding is a draft. Read the cited pages, then confirm or dismiss.
      </p>
    </aside>
  )
}

// The working app. It needs the local server (python -m nyaya), which opens this page with a one-time key.
export default function AppPage() {
  const [expired, setExpired] = useState(!token)
  const [open, setOpen] = useState<CaseInfo | null>(null)
  const [model, setModel] = useState<Model | null>(null)
  const [cloud, setCloud] = useState<CloudState | null>(null)

  useEffect(() => {
    if (token) {
      api<Model>('/model').then(setModel).catch(() => {})
      api<CloudState>('/cloud').then(setCloud).catch(() => {})
    }
    const onExpired = () => setExpired(true)
    const onCloud = (e: Event) => setCloud((e as CustomEvent<CloudState>).detail)
    window.addEventListener('nyaya-token-expired', onExpired)
    window.addEventListener('nyaya-cloud', onCloud)
    return () => {
      window.removeEventListener('nyaya-token-expired', onExpired)
      window.removeEventListener('nyaya-cloud', onCloud)
    }
  }, [])

  function home(anchor?: string) {
    setOpen(null)
    if (anchor) setTimeout(() => document.getElementById(anchor)?.scrollIntoView({ behavior: 'smooth' }), 50)
  }

  if (expired) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <h1 className="text-2xl font-semibold">Start Nyaya AI on your laptop</h1>
        <p className="text-muted-foreground mt-3">
          The app works on your own machine, so case files stay there. Run <code className="bg-muted rounded px-1">python -m nyaya</code> and
          use the browser window it opens. If you restarted it, close this tab.
        </p>
      </div>
    )
  }

  return (
    <div className="grid w-full gap-6 px-6 lg:px-10 py-6 lg:grid-cols-[14rem_minmax(0,1fr)]">
      <div className="print:hidden"><Sidebar open={open} onHome={home} model={model} cloud={cloud} /></div>
      <div className="min-w-0">
        {model && !model.local && (
          <p className="mb-4 rounded-xl border border-orange-200 bg-orange-50 px-4 py-2.5 text-sm text-orange-900 print:hidden">
            Analysis sends paragraph text to a hosted model (Gemini). Use fictional cases only. Real cases use Ollama on this laptop.
          </p>
        )}
        {open ? <CaseView key={open.id} info={open} onClose={() => setOpen(null)} /> : <CaseList onOpen={setOpen} />}
      </div>
      <Toaster richColors position="bottom-right" />
    </div>
  )
}
