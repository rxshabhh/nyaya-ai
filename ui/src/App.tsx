import { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { CaseList } from '@/components/CaseList'
import { CaseView } from '@/components/CaseView'
import { Legal } from '@/components/Legal'
import { Toaster } from '@/components/ui/sonner'
import { token, type CaseInfo } from '@/lib/api'

export default function App() {
  const [expired, setExpired] = useState(!token)
  const [open, setOpen] = useState<CaseInfo | null>(null)

  useEffect(() => {
    const onExpired = () => setExpired(true)
    window.addEventListener('nyaya-token-expired', onExpired)
    return () => window.removeEventListener('nyaya-token-expired', onExpired)
  }, [])

  return (
    <div className="bg-background text-foreground flex min-h-svh flex-col">
      <header className="border-b print:hidden">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <button type="button" onClick={() => setOpen(null)} className="text-lg font-semibold tracking-tight">Nyaya AI</button>
          <span className="text-muted-foreground hidden items-center gap-1.5 text-xs sm:flex">
            <ShieldCheck className="size-3.5" aria-hidden /> Runs on this laptop. Case files never leave it.
          </span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        {expired ? (
          <div className="mx-auto max-w-md py-16 text-center">
            <h1 className="text-xl font-semibold">Open Nyaya AI from the launcher</h1>
            <p className="text-muted-foreground mt-2 text-sm">
              This page needs the one-time key the launcher creates. Run <code className="bg-muted rounded px-1">python -m nyaya serve</code> and
              use the window it opens. If you restarted the launcher, close this tab.
            </p>
          </div>
        ) : open ? (
          <CaseView key={open.id} info={open} onClose={() => setOpen(null)} />
        ) : (
          <CaseList onOpen={setOpen} />
        )}
      </main>

      <footer className="text-muted-foreground grid gap-1 border-t px-4 py-3 text-center text-xs print:hidden">
        <span>Every finding is a draft for the advocate to confirm or dismiss. Nyaya AI does not give legal advice.</span>
        <Legal />
      </footer>
      <Toaster richColors position="bottom-right" />
    </div>
  )
}
