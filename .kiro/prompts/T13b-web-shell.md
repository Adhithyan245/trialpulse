Task T13b: the web app shell and design system (React + Vite + TypeScript + Tailwind).

You cannot run shell commands or use the web in this project. The reviewer runs
`npm install` and `npm run build` in web/ and reports errors back. Read
.kiro/steering/design.md and trialpulse/api/app.py (the API you will call) first.

Files you may create: everything under web/ (except web/node_modules and web/dist).
Also edit .gitignore: keep everything, and add these two lines right after the line
"!data/derived/metrics*.json":
  !data/derived/validation/
  !data/derived/trial_locations.json
(the recorded runs and the trial-location cache must ship with the app for replay mode).
Nothing else.

web/package.json: name "trialpulse-web", private, type "module", scripts
  dev "vite", build "tsc -b && vite build", preview "vite preview".
  dependencies (exact versions): react 18.3.1, react-dom 18.3.1, recharts 2.13.3,
  motion 11.11.17, lucide-react 0.454.0, d3-geo 3.1.1, three 0.169.0,
  @react-three/fiber 8.17.10, @react-three/drei 9.115.0,
  @fontsource/ibm-plex-sans 5.1.0, @fontsource/ibm-plex-mono 5.1.0.
  devDependencies: vite 5.4.10, @vitejs/plugin-react 4.3.3, typescript 5.6.3,
  tailwindcss 3.4.14, postcss 8.4.47, autoprefixer 10.4.20, @types/react 18.3.12,
  @types/react-dom 18.3.1, @types/three 0.169.0, @types/d3-geo 3.1.0.
  (Use only these; no router, no state library, no UI kit.)
web/vite.config.ts: react plugin; server.proxy "/api" -> "http://127.0.0.1:8000".
web/tsconfig.json (+ tsconfig.app.json / tsconfig.node.json as Vite's template does):
  strict true, jsx react-jsx, target ES2020, moduleResolution bundler, noEmit.
web/tailwind.config.js + web/postcss.config.js: Tailwind colors mapped to CSS variables
  (ink, surface, card, line, text, muted, accent, pass, watch, held, and *-soft variants),
  fontFamily sans "IBM Plex Sans", mono "IBM Plex Mono". darkMode: ["class",
  '[data-theme="dark"]'] plus media fallback via the CSS variables below.
web/index.html: title "TrialPulse", root div, loads /src/main.tsx.

web/src/styles.css: @tailwind base/components/utilities; import the fontsource CSS for
  ibm-plex-sans 400/500/600 and ibm-plex-mono 400/500 in main.tsx instead. Define tokens
  on :root (light) and redefine them under @media (prefers-color-scheme: dark) and
  [data-theme="dark"]:
    light: ink #0E1A24, surface #F4F6F7, card #FFFFFF, line #D8DFE3, text #13212B,
    muted #5A6A75, accent #0F7C86, accent-soft #DDEFF0, pass #1E7A4C, pass-soft #E1F2E8,
    watch #A86400, watch-soft #FBEFDC, held #B3261E, held-soft #FBE4E2
    dark: ink #08121A, surface #0F1920, card #15222B, line #263640, text #E2EBEF,
    muted #9AADB7, accent #4FC2CC, accent-soft #143A3F, pass #74D29C, pass-soft #15301F,
    watch #F0B460, watch-soft #3A2B14, held #FF8A80, held-soft #3B1C1A
  body uses surface background and text color; tabular-nums utility for numbers;
  visible focus ring (2px accent); prefers-reduced-motion disables animations.

web/src/types.ts: TypeScript types matching the API: Participant, Site, Trial,
  ClockDay {day, participants: [{participant_id, site_id, resting_hr: number|null, worn,
  drift, non_wear, diary_conflict}]}, Claim {claim_id, type, text, cited_record_ids},
  Report {report_id, participant_id, as_of, window_start, window_end, claims, abstained,
  model_id, prompt_version}, GateCheck {dimension, passed, explanation}, GateResult
  {report_id, verdict: "pass"|"hold", checks, pulseeval_commit}, EvidenceRequest
  {request_id, report_id, participant_id, failed_dimension, kind, question_text, sent_at,
  reply_record_id, status}, Reading {record_id, kind, name, value, unit, event_time,
  recorded_at, source, participant_id, site_id}, RunSummary {case_id, participant_id, day,
  fault, raw_verdict, final_verdict, rounds, models_used}, RunRecord {case_id,
  participant_id, day, fault, ground_truth_note, raw: {report, gate, verdict, failed},
  pipeline: {drafts, gates, requests, replies, final_verdict, rounds}, models_used,
  recorded?}, AuditEntry, Metrics.
web/src/api.ts: tiny fetch client: getJSON(path) / postJSON(path, body) that send the
  "X-Role" header from the current role; functions health(), trial(), clock(),
  participantSeries(pid, day), runs(), run(caseId), negativeControl(caseId), metrics(),
  audit(reportId?), auditVerify(), sign(body), tamper(entryId). Throw an Error with the
  server's detail on non-2xx; never return made-up data.
web/src/checks.ts: the 7 checkpoint rings and how gate dimensions map to them:
  RINGS = [
   {id:"time", label:"Time", dims:["temporal_consistency"], plain:"Only uses data that
     existed at report time"},
   {id:"evidence", label:"Evidence", dims:["evidence_grounding"], plain:"Cites the right
     records"},
   {id:"numbers", label:"Numbers", dims:["recompute"], plain:"Every number matches the
     records"},
   {id:"coverage", label:"Coverage", dims:["missing_data"], plain:"Is honest about
     missing days"},
   {id:"conflict", label:"Conflict", dims:["contradiction"], plain:"Names wearable vs
     diary conflicts"},
   {id:"certainty", label:"Certainty", dims:["uncertainty"], plain:"Sounds as sure as
     the data allows"},
   {id:"causation", label:"Causation", dims:["causal_restraint","negative_control"],
     plain:"Never blames the drug without support"}]
  ringForDimension(dimension: string) -> ring id (prefix before ":"); claimIdOf(dimension)
  -> the part after ":"; checksForClaim(gate, claimId) and reportLevelChecks(gate)
  (dimensions whose suffix is the report_id).
web/src/role.tsx: React context for role ("monitor" | "coordinator" | "safety_reviewer"),
  default "monitor", kept in localStorage inside try/catch.
web/src/App.tsx: hash routing without a library: "#/" Landing, "#/trial" Scene 1,
  "#/checkpoint" Scene 2, "#/seal" Scene 3, "#/verified" Scene 4, "#/proof" Scene 5.
  Wrap scenes in <Shell>.
web/src/components/Shell.tsx: left ink navigation with the TrialPulse wordmark and the
  five scenes (numbered 1-5, they are a real sequence), role switcher (three buttons),
  a mode badge from /api/health ("Recorded runs" in replay mode, "Live AI" in live mode),
  a theme toggle (light/dark/system, sets data-theme on <html>), and a "Synthetic data"
  ribbon pinned at the top of the working area. Collapses to a top bar under 768px.
web/src/components/StatusPill.tsx: pass / watch / held pill with a lucide icon
  (CheckCircle2, AlertTriangle, ShieldAlert) and a text label; never color alone.
web/src/components/Landing.tsx: the line "The AI drafts. Deterministic checks verify.
  Humans decide." as the headline, one sentence under it ("TrialPulse watches clinical
  trial participants through WHOOP-style wearables, checks every claim an AI makes about
  them, and asks for the missing evidence before a doctor signs."), a "Start the demo"
  button (goes to #/checkpoint), and the three role buttons with one line each. Show the
  real headline numbers from /api/metrics validation (cases, raw held, unsafe reaching
  monitor) if present; if the request fails, show nothing for them (no fake numbers).
web/src/scenes/*.tsx: for this task, Scene1Trial, Scene2Checkpoint, Scene3Seal,
  Scene4Verified, Scene5Proof each render their scene title, the one-line purpose from
  design.md, and a short "Built in the next task" note. (Scene 2 is the next task.)
web/src/main.tsx: imports fonts and styles, renders <RoleProvider><App/></RoleProvider>.

Done when the reviewer's `npm run build` succeeds with no TypeScript errors. When
finished, list every file you created or changed and stop.
