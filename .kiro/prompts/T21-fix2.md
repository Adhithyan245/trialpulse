Task T21-fix2: two small landing details.

You cannot run shell commands or use the web in this project; the reviewer checks it.
Files you may edit: web/src/components/Landing.tsx and files under
web/src/components/landing/. Nothing else.

1. Format the stat numbers with thousands separators (3131 -> "3,131") using
   Number.prototype.toLocaleString("en-US").
2. The proof strip appears a moment after the page loads and pushes "How it works" down.
   While /api/metrics is loading, render the four tiles as fixed-height skeleton tiles
   (same size, muted pulse background, no numbers, aria-busy); if the request fails or a
   value is missing, hide only that tile as before. Respect prefers-reduced-motion (no
   pulse).
When finished, list the files you changed and stop.
