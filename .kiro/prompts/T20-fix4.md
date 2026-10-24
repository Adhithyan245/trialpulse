Task T20-fix4: two finishing fixes for the 3D tunnel.

You cannot run shell commands or use the web in this project; the reviewer checks the
browser and the build output. Files you may edit: web/src/scenes/checkpoint/Tunnel3D.tsx,
web/src/scenes/checkpoint/WebGLBoundary.tsx, web/src/scenes/Scene2Checkpoint.tsx.

1. In the dark theme the "not applicable" rings render almost black and disappear against
   the background. Use the --muted CSS token color for idle and dimmed rings (dimmed at
   opacity 0.45, idle at 0.8) instead of --line, so every ring stays visible in both
   themes. Also pull the camera back ~10% so the first ring ("Time") is not cut at the
   left edge.
2. The 3D code is leaking into the main bundle: after adding the 3D tunnel the main chunk
   grew from ~293 kB to ~730 kB, while Tunnel3D's own chunk is ~844 kB. Something outside
   Tunnel3D.tsx imports from three, @react-three/fiber or @react-three/drei, or imports a
   value (not only a type) from Tunnel3D.tsx. Make sure Scene2Checkpoint.tsx and
   WebGLBoundary.tsx import NOTHING from those packages or from Tunnel3D.tsx except via
   React.lazy(() => import("./checkpoint/Tunnel3D")) — move any shared helper into a
   file that does not import three, and use `import type` for types. The WebGL capability
   check must use only document.createElement("canvas").
When finished, list the files you changed and stop.
