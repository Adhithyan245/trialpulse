Task T14-fix5: one build error after renaming sequence steps.

You cannot run shell commands or use the web in this project; the reviewer builds it.
File you may edit: web/src/scenes/checkpoint/RingTunnel.tsx only.

  src/scenes/checkpoint/RingTunnel.tsx(22,34): error TS2367: This comparison appears to be
  unintentional because the types '"intro" | "travel" | "requesting" | "received" |
  "desk"' and '"requests"' have no overlap.
The step "requests" no longer exists; it became "requesting" and "received". Update that
comparison to the new step names with the same intent. When finished, list the file you
changed and stop.
