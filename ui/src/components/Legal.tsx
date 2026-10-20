import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

const PAGES = {
  Privacy: [
    'Nyaya AI runs entirely on this laptop. It has no account, no cloud service and no telemetry. Case files are never uploaded.',
    'Documents and findings are encrypted with AES-256-GCM. The key is derived from your passphrase with Argon2id. The passphrase is never stored, so it cannot be recovered. If you lose it, the case cannot be opened.',
    'The case code name you type is stored unencrypted so the case list can show it. Do not use a client name there.',
    'Language-model work is done by Ollama on this machine. Nyaya AI refuses to send text to any address that is not this machine.',
    'The case key stays in memory while a case is unlocked. Cases lock after 15 idle minutes and when you press Lock. Anyone with access to this unlocked computer can read an unlocked case.',
  ],
  Terms: [
    'Nyaya AI is a research aid for advocates. It lists possible contradictions and omissions between statements and shows the exact quote and page for each. It does not give legal advice and does not decide anything.',
    'Every finding is a draft. You must read the cited passages yourself and confirm or dismiss each finding before relying on it. A finding can be wrong, and the tool can miss conflicts, especially paraphrased ones.',
    'Only digital English text is supported. Scanned documents are refused. A claim whose quote is not found in the cited paragraph is rejected and never used.',
    'The software is provided as is, without warranty. You are responsible for the confidentiality and backup of your case files and passphrases.',
  ],
} as const

export function Legal() {
  return (
    <span className="flex justify-center gap-4">
      {Object.entries(PAGES).map(([title, paras]) => (
        <Dialog key={title}>
          <DialogTrigger className="hover:underline">{title}</DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription className="sr-only">{title} of Nyaya AI</DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 text-sm leading-relaxed">{paras.map((t) => <p key={t}>{t}</p>)}</div>
          </DialogContent>
        </Dialog>
      ))}
    </span>
  )
}
