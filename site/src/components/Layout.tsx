import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Menu, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { NAV, REPO } from '@/content'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm transition-colors hover:text-foreground ${isActive ? 'text-foreground font-medium' : 'text-muted-foreground'}`

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
      <span className="bg-primary text-primary-foreground grid size-7 place-items-center rounded-md text-sm" aria-hidden>न्</span>
      Nyaya AI
    </Link>
  )
}

function Header() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  useEffect(() => { setOpen(false) }, [pathname])
  return (
    <header className="bg-background/85 sticky top-0 z-40 border-b backdrop-blur">
      <div className="flex h-14 w-full items-center justify-between gap-4 px-6 lg:px-10">
        <Brand />
        <nav aria-label="Main" className="hidden items-center md:flex">
          {NAV.map((n) => <NavLink key={n.to} to={n.to} className={linkClass}>{n.label}</NavLink>)}
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline" className="hidden sm:inline-flex"><Link to="/get-started">Get started</Link></Button>
          <Button asChild size="sm" className="hidden sm:inline-flex"><Link to="/app">Open app</Link></Button>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" className="md:hidden" aria-label="Open menu"><Menu /></Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <SheetHeader><SheetTitle>Menu</SheetTitle></SheetHeader>
              <nav aria-label="Mobile" className="grid gap-1 px-4">
                {[{ to: '/app', label: 'Open app' }, ...NAV, { to: '/get-started', label: 'Get started' }, { to: '/contact', label: 'Contact' }].map((n) => (
                  <NavLink key={n.to} to={n.to} className={({ isActive }) => `rounded-md px-3 py-2.5 text-base ${isActive ? 'bg-muted font-medium' : ''}`}>{n.label}</NavLink>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}

const COLS = [
  { h: 'Product', links: [['/features', 'Features'], ['/how-it-works', 'How it works'], ['/security', 'Security'], ['/get-started', 'Get started']] },
  { h: 'Resources', links: [['/docs', 'Documentation'], ['/faq', 'FAQ'], ['/about', 'About and roadmap'], ['/contact', 'Contact']] },
  { h: 'Legal', links: [['/privacy', 'Privacy'], ['/terms', 'Terms']] },
] as const

function Footer() {
  return (
    <footer className="bg-muted/50 border-t">
      <div className="grid w-full gap-8 px-6 lg:px-10 py-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="grid content-start gap-3">
          <Brand />
          <p className="text-muted-foreground max-w-xs text-sm">
            Offline cross-examination prep for Indian advocates. Case files never leave your laptop.
          </p>
          <p className="text-muted-foreground flex items-center gap-1.5 text-xs"><ShieldCheck className="size-3.5" aria-hidden /> Free and open source, MIT licence</p>
        </div>
        {COLS.map((c) => (
          <nav key={c.h} aria-label={c.h}>
            <h2 className="mb-3 text-sm font-semibold">{c.h}</h2>
            <ul className="grid gap-2 text-sm">
              {c.links.map(([to, l]) => (
                <li key={to}><Link to={to} className="text-muted-foreground hover:text-foreground">{l}</Link></li>
              ))}
              {c.h === 'Resources' && <li><a href={REPO} className="text-muted-foreground hover:text-foreground" rel="noreferrer" target="_blank">GitHub</a></li>}
            </ul>
          </nav>
        ))}
      </div>
      <div className="text-muted-foreground border-t px-4 py-4 text-center text-xs">
        Every finding is a draft for the advocate to confirm or dismiss. Nyaya AI does not give legal advice.
      </div>
    </footer>
  )
}

export function Layout() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return (
    <div className="bg-background text-foreground flex min-h-svh flex-col">
      <a href="#main" className="bg-primary text-primary-foreground sr-only z-50 rounded-md px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2">Skip to content</a>
      <Header />
      <main id="main" className="flex-1"><Outlet /></main>
      <Footer />
    </div>
  )
}
