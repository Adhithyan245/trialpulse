Task T20: a 3D version of the checkpoint tunnel, with the 2D tunnel as fallback.

You cannot run shell commands or use the web in this project; the reviewer builds and
checks it in a browser. Read .kiro/steering/design.md, web/src/scenes/Scene2Checkpoint.tsx,
web/src/scenes/checkpoint/RingTunnel.tsx, web/src/scenes/checkpoint/useSequence.ts and
web/src/checks.ts first. TypeScript strict (no unused locals/params/imports).

Files you may create: web/src/scenes/checkpoint/Tunnel3D.tsx,
web/src/scenes/checkpoint/WebGLBoundary.tsx. You may edit
web/src/scenes/Scene2Checkpoint.tsx only to add the 3D/2D switch described below.
Nothing else. Installed and allowed: three 0.169, @react-three/fiber 8.17, @react-three/drei
9.115 (use only Html, RoundedBox, OrbitControls from drei; do NOT use drei <Text> or any
component that downloads fonts, models or environment maps from the internet: the app must
work offline). No new dependencies.

Tunnel3D (props: the same data RingTunnel receives: rings, the current draft's claims,
gate checks, the current sequence step, reduced-motion flag):
 - A <Canvas> (height 360px, dpr [1, 2], camera at an angle looking down the tunnel)
   with 7 torus rings (radius 1.1, tube 0.06) spaced 1.6 apart along the z axis, in
   RINGS order, each with its label as an <Html> element under it (small text, theme
   token colors via CSS classes on the Html content).
 - Ring colors read from CSS variables at runtime (getComputedStyle on
   document.documentElement: --line for idle, --pass, --held, --accent), re-read when
   data-theme changes. Background transparent (Canvas gl alpha) so the card shows.
 - The active claim is a small RoundedBox token with an <Html> label "C3" that moves
   along z from in front of ring 1 toward the current ring index of the travel step
   (smooth lerp in useFrame; with reduced motion, jump). A passing ring flashes the pass
   color briefly; a failing ring turns held and the token stops inside it and turns held.
   Rings with no check for the claim are dimmed (opacity 0.35).
 - After the travel steps of a draft, the rings where claims were stopped stay held.
 - Gentle OrbitControls (no zoom, limited rotation) so judges can tilt it.
WebGLBoundary: a React error boundary + a WebGL capability check
 (canvas.getContext("webgl2") || getContext("webgl")); renders children when OK, else the
 given fallback. Any render error inside the 3D scene also shows the fallback.
Scene2Checkpoint: add a small segmented switch "3D | 2D" next to the speed toggle.
 Default 3D when WebGL is available and prefers-reduced-motion is not set, else 2D.
 Load Tunnel3D with React.lazy + Suspense (fallback: the 2D RingTunnel) so the 2D path
 does not download three.js. The current-claim panel, queue, inbox and desk stay as they
 are and keep working in both modes. Keep the 2D RingTunnel unchanged.
When finished, list every file you created or changed and stop.
