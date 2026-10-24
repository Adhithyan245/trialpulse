Task T14-fix2: three unused-symbol build errors.

You cannot run shell commands or use the web in this project; the reviewer builds it.
Files you may edit: web/src/scenes/checkpoint/CurrentClaimPanel.tsx,
web/src/scenes/checkpoint/RingTunnel.tsx, .kiro/steering/tech.md. Nothing else.

`npm run build` fails (tsconfig has noUnusedLocals / noUnusedParameters):
  src/scenes/checkpoint/CurrentClaimPanel.tsx(13,50): error TS6133: 'step' is declared but
    its value is never read.
  src/scenes/checkpoint/RingTunnel.tsx(3,35): error TS6133: 'claimIdOf' is declared but
    its value is never read.
  src/scenes/checkpoint/RingTunnel.tsx(4,15): error TS6196: 'GateCheck' is declared but
    never used.
Remove the unused symbols (if a prop is unused, remove it from the component's props type
and stop passing it from Scene2Checkpoint.tsx only if that is the only change needed
there; you may edit Scene2Checkpoint.tsx for that single purpose).
Also append this line to .kiro/steering/tech.md so this stops recurring:
"TypeScript is strict with noUnusedLocals and noUnusedParameters: never leave unused
imports, variables or props; the reviewer's build fails on them."
When finished, list the files you changed and stop.
