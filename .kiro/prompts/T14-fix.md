Task T14-fix: make the checkpoint scene build.

You cannot run shell commands or use the web in this project; the reviewer builds it.
Files you may edit: web/src/scenes/Scene2Checkpoint.tsx, files in
web/src/scenes/checkpoint/, and .gitignore (add one line "*.tsbuildinfo" at the end).
Nothing else. Do not change behavior beyond what these errors need.

`npm run build` (tsc -b && vite build) fails with:
  src/scenes/checkpoint/RingTunnel.tsx(42,15): error TS6133: 'ringChecks' is declared but
    its value is never read.
  src/scenes/checkpoint/useSequence.ts(2,28): error TS6196: 'EvidenceRequest' is declared
    but never used.
  src/scenes/Scene2Checkpoint.tsx(64,25): error TS2345: Argument of type 'unknown' is not
    assignable to parameter of type 'SetStateAction<SeriesData | null>'.
For the third: give the API call a proper return type (add a typed function to the scene
or cast the parsed JSON to SeriesData after checking it has "metrics" and "bands"), not
`any`. While you are there, replace any `(x as any)` you added in T14 with proper type
narrowing (discriminated unions on step.type). When finished, list the files you changed
and stop.
