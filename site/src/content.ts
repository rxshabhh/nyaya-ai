// All site copy that more than one page uses. Facts come from the project README and the shipped build;
// status labels say plainly what is built and what is planned.
export const REPO = 'https://github.com/rxshabhh/nyaya-ai'

export const NAV = [
  { to: '/features', label: 'Features' },
  { to: '/how-it-works', label: 'How it works' },
  { to: '/security', label: 'Security' },
  { to: '/docs', label: 'Docs' },
  { to: '/faq', label: 'FAQ' },
  { to: '/about', label: 'About' },
]

export const FEATURES = [
  {
    title: 'Contradictions, field by field',
    body: 'Compares dates, times, places and amounts for the same event across a witness’s statements. “Night of 12/13.03.2021” against “12.03.2021” is understood as overlapping, not flagged.',
  },
  {
    title: 'Omissions you can’t search for',
    body: 'Finds what a witness said in one statement and left out of the other, ranked with likely-material items (weapon, threat, injury, eyewitness) first.',
  },
  {
    title: 'Every quote verified by code',
    body: 'A language model only proposes claims. Code rejects any claim whose quote is not word for word in the cited paragraph, or whose date, time, place or amount is not inside the quote.',
  },
  {
    title: 'Exact citations',
    body: 'Each finding shows both quotes side by side with document, page and paragraph. The citation is set by the software, never read from the model.',
  },
  {
    title: 'Confirm or dismiss',
    body: 'You decide on every finding. Your decisions are saved with the case and survive a re-run. Findings that disappear after a re-run are kept, marked, and never silently deleted.',
  },
  {
    title: 'Encrypted case vault',
    body: 'Each case has its own passphrase. Documents, names and findings are encrypted at rest with AES-256-GCM. Cases auto-lock after 15 idle minutes.',
  },
  {
    title: 'Works fully offline',
    body: 'No telemetry. The local AI model runs on your laptop. The optional cloud locker stores only encrypted archives that AWS cannot read.',
  },
  {
    title: 'Built for Snapdragon X',
    body: 'The extraction and pairing stages are designed for the Hexagon NPU, with a CPU fallback so everything runs today on any Windows laptop.',
  },
]

export const STEPS = [
  { title: 'Add the documents', body: 'Upload each witness’s police statement, FIR, chargesheet extract and court testimony as text, digital PDF or Word. Confirm the witness, type and date on a short form.' },
  { title: 'Read paragraph by paragraph', body: 'Every paragraph gets an address: document, page, paragraph. That address is the citation you will see later.' },
  { title: 'A local model proposes claims', body: 'A small language model on your laptop reads each paragraph and lists what happened: who, what event, when, where, how much, with the exact quote.' },
  { title: 'Code verifies every claim', body: 'Claims whose quote is not in the cited paragraph, or whose details are not in the quote, are rejected and never reach you. You can still see what was rejected and why.' },
  { title: 'Pair and compare', body: 'Claims about the same event by the same witness are paired, by event label or by meaning when wording differs, then compared for contradictions and omissions.' },
  { title: 'Review and decide', body: 'Read the side-by-side quotes, Confirm or Dismiss each finding, and print the list to PDF for your notes.' },
]

export const AUDIENCE = [
  { title: 'Defence and prosecution advocates', body: 'Prepare cross-examination against hundreds of pages without reading each side by side.' },
  { title: 'Junior advocates and chambers', body: 'Give juniors a verified, cited starting list instead of a blank stack of files.' },
  { title: 'Legal researchers', body: 'Trace exactly where two statements diverge, with quotes you can check in seconds.' },
]

export const FAQ = [
  {
    q: 'Does any of my case data leave my laptop?',
    a: 'No. There is no telemetry, and the optional cloud locker only stores encrypted archives that AWS cannot read. The language model runs locally through Ollama, and the app refuses to contact any address other than your own machine. Documents and findings are stored encrypted on disk.',
  },
  {
    q: 'Can the AI invent a quote or a page number?',
    a: 'A model can try, but it cannot get past the verification gate. Every quote must appear word for word in the cited paragraph, and every date, time, place and amount must appear inside the quote. Page and paragraph are attached by the software, not by the model. Anything that fails is shown only under “Rejected claims”.',
  },
  {
    q: 'Does it give legal advice or decide what is material?',
    a: 'No. Every finding is a draft. Omissions are ranked with a simple keyword heuristic (weapon, threat, injury, identification, eyewitness) to help you read the likeliest ones first. You decide what is material and what to use.',
  },
  {
    q: 'Which documents and languages are supported?',
    a: 'Plain text, digital PDF and Word (.docx), in English. Scanned PDFs are refused with a message naming the pages, because OCR is not in version 1. Indian-language support is not available yet.',
  },
  {
    q: 'What if I forget a case passphrase?',
    a: 'It cannot be recovered. There is no reset and no copy of the key anywhere else. Keep the passphrase somewhere safe. You can export an encrypted archive of a case as a backup, but it also needs the same passphrase.',
  },
  {
    q: 'How accurate is it?',
    a: 'On the five fictional test cases the checks find every planted contradiction and omission with no false flags, and the gate rejects every planted bad claim. That uses pre-written claims. Accuracy with the live language model on real files has not been measured yet, and we say so rather than guess.',
  },
  {
    q: 'Do I need a Snapdragon laptop?',
    a: 'No. It runs on any Windows laptop using the CPU. The NPU stages are designed for Snapdragon X and will be faster and lighter on battery there, but they are not required.',
  },
  {
    q: 'What does it cost?',
    a: 'Nothing. Nyaya AI is free and open source under the MIT license.',
  },
]

export const STATUS = [
  { item: 'Parse text, digital PDF and Word with page and paragraph citations', status: 'Built' },
  { item: 'Verification gate for every claim', status: 'Built' },
  { item: 'Contradictions and omissions, paired per witness', status: 'Built' },
  { item: 'Encrypted case vault and encrypted findings store', status: 'Built' },
  { item: 'Local app with Confirm and Dismiss, export and restore of cases', status: 'Built' },
  { item: 'Claim extraction with a local model through Ollama', status: 'Built, not yet measured on real files' },
  { item: 'Embedding similarity for differently worded claims', status: 'Built, threshold untuned' },
  { item: 'Embedder on the Hexagon NPU', status: 'Profiled on Qualcomm AI Hub: 219 of 219 layers on NPU, 1.7 ms' },
  { item: 'Claim extraction on the Hexagon NPU (Genie)', status: 'Planned, needs a Snapdragon X device' },
  { item: 'Chargesheet splitting per witness', status: 'Planned' },
  { item: 'OCR for scanned documents, Indian languages', status: 'Not in version 1' },
  { item: 'One-click Windows installer', status: 'Planned' },
]

export const PRIVACY = [
  ['What this covers', 'This policy covers the Nyaya AI software you run on your own computer and this website.'],
  ['The software collects nothing', 'Nyaya AI has no telemetry. It never sends readable case files, findings, usage data or crash reports anywhere. The optional cloud locker (an AWS account from your administrator) receives only encrypted archives. Language-model work is done by Ollama on your machine, and the software refuses any model address that is not your own machine.'],
  ['What is stored on your computer', 'Each case is a folder holding encrypted documents, an encrypted index of document names and details, and an encrypted findings database. They are encrypted with AES-256-GCM under a random key that is itself locked by a key derived from your passphrase with Argon2id. The case code name you type is the one thing stored unencrypted, so the case list can show it. Do not use a client’s name as a code name.'],
  ['Your passphrase', 'It is never stored and cannot be recovered. If you lose it, nobody, including us, can open the case.'],
  ['While a case is open', 'The case key is held in memory while a case is unlocked. Cases lock after 15 idle minutes or when you press Lock. Anyone who can use your unlocked computer can read an unlocked case. Python cannot guarantee that memory is wiped, so the protection is aimed at a lost or stolen laptop, not at an attacker inspecting a running machine.'],
  ['This website', 'This website is static. It has no forms, no accounts, no analytics and sets no cookies. Third-party fonts and scripts are served from the site itself.'],
  ['Contact', 'Questions about privacy can be raised on the project’s GitHub issues page.'],
]

export const TERMS = [
  ['Acceptance', 'By using Nyaya AI you accept these terms. If you do not accept them, do not use it.'],
  ['A research aid, not legal advice', 'Nyaya AI lists possible contradictions and omissions between statements and shows the exact quotes and citations. It does not give legal advice, does not decide what is material, and does not replace your professional judgment.'],
  ['Every finding is a draft', 'You must read the cited passages yourself and confirm or dismiss each finding before relying on it. A finding can be wrong, and the software can miss conflicts, especially when statements are paraphrased.'],
  ['Limits of the software', 'Version 1 reads English text, digital PDF and Word files only. Scanned documents are refused. Parsing of PDF layout is heuristic and should be checked against the original.'],
  ['Your files and passphrases', 'You are responsible for the confidentiality of your case files, for keeping your passphrases safe, and for keeping backups. A lost passphrase cannot be recovered.'],
  ['Licence', 'The software is released under the MIT licence. It is provided as is, without warranty of any kind, and the authors are not liable for any loss arising from its use.'],
  ['Changes', 'These terms may change as the project does. The current version is the one shown on this page.'],
]
