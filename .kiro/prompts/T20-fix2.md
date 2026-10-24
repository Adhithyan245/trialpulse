Task T20-fix2: the 3D tunnel's framing is wrong.

You cannot run shell commands or use the web in this project; the reviewer checks the
browser. File you may edit: web/src/scenes/checkpoint/Tunnel3D.tsx only.

What the reviewer saw (canvas ~580x450): the torus rings lie flat like hoops on the floor
(their hole points up), they are huge and the camera is so close that only the first two
rings ("Time", "Evidence") are visible, cut off at the bottom edge.
Required:
 - Rings stand up as gates that the token passes THROUGH: the ring's hole must face along
   the tunnel axis. A Three.js TorusGeometry already lies in the XY plane with its hole
   along Z, so with the tunnel running along Z, use NO rotation on the rings (remove any
   rotation such as [Math.PI/2, 0, 0]).
 - Ring i at position [0, 0, -i * 1.6] (z from 0 to -9.6); token moves along the same axis.
 - Camera: perspective, fov 38, position [5.5, 2.4, 4.5], looking at the tunnel center
   [0, 0, -4.8] (set via a <PerspectiveCamera makeDefault> or the Canvas camera prop plus
   a useEffect/useFrame lookAt, and OrbitControls target [0, 0, -4.8]). All 7 rings and
   their labels must be inside the frame at 580x450 and at 340x360; if the canvas is
   narrower than 480px, move the camera back (scale its distance by 480 / width).
 - Labels (<Html>) sit just below each ring (y = -1.35) with small muted text and
   pointer-events none; they must not cover the next ring.
 - Lights: ambient 0.6 + one directional light so the rings read as tubes.
When finished, list the file you changed and stop.
