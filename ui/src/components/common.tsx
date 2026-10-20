import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const MIN = 8 // matches the vault's minimum

// One dialog for create, unlock, demo and change-passphrase. `confirm` asks for the passphrase twice.
export function PassphraseDialog(props: {
  trigger: ReactNode
  title: string
  description: ReactNode
  submit: string
  withLabel?: boolean
  confirm?: boolean
  onSubmit: (passphrase: string, label: string) => Promise<unknown>
}) {
  const [open, setOpen] = useState(false)
  const [label, setLabel] = useState('')
  const [pass, setPass] = useState('')
  const [again, setAgain] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function reset(o: boolean) {
    setOpen(o)
    if (!o) {
      setLabel('')
      setPass('')
      setAgain('')
      setError('')
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (props.confirm && pass.length < MIN) return setError(`Use at least ${MIN} characters.`)
    if (props.confirm && pass !== again) return setError('The two passphrases do not match.')
    setBusy(true)
    setError('')
    try {
      await props.onSubmit(pass, label)
      reset(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogTrigger asChild>{props.trigger}</DialogTrigger>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>{props.title}</DialogTitle>
            <DialogDescription>{props.description}</DialogDescription>
          </DialogHeader>
          {props.withLabel && (
            <div className="grid gap-2">
              <Label htmlFor="case-label">Case code name</Label>
              <Input id="case-label" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. SC-114 robbery" required autoFocus />
              <p className="text-muted-foreground text-xs">Shown in the case list without encryption. Do not use the client's name.</p>
            </div>
          )}
          <div className="grid gap-2">
            <Label htmlFor="pass">Passphrase</Label>
            <Input id="pass" type="password" value={pass} onChange={(e) => setPass(e.target.value)} required autoFocus={!props.withLabel} autoComplete={props.confirm ? 'new-password' : 'current-password'} />
          </div>
          {props.confirm && (
            <div className="grid gap-2">
              <Label htmlFor="pass2">Repeat passphrase</Label>
              <Input id="pass2" type="password" value={again} onChange={(e) => setAgain(e.target.value)} required autoComplete="new-password" />
              <p className="text-muted-foreground text-xs">There is no recovery. A lost passphrase means the case cannot be opened.</p>
            </div>
          )}
          {error && <p role="alert" className="text-destructive text-sm">{error}</p>}
          <DialogFooter>
            <Button type="submit" disabled={busy}>{busy ? 'Working…' : props.submit}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function ConfirmAction(props: { trigger: ReactNode; title: string; description: ReactNode; action: string; onConfirm: () => void }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>{props.trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{props.title}</AlertDialogTitle>
          <AlertDialogDescription>{props.description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={props.onConfirm}>{props.action}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
