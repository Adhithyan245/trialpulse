Task T21-fix: the landing illustration's evidence arrow ends in empty space.

You cannot run shell commands or use the web in this project; the reviewer checks it.
Files you may edit: the landing pipeline illustration component under
web/src/components/landing/ (and Landing.tsx only if the SVG lives there).

In the pipeline SVG, the amber "asks for evidence" curve starts at the held ring and ends
with an arrowhead in empty space below-left, far from the wearable. It must loop back to
the wearable pulse line: start under the held (red) ring, curve down and left beneath the
"AI draft" card, and end with its arrowhead pointing up into the bottom of the wearable
pulse line (just under the "Wearable" label's line). Keep the label "asks for evidence"
centered on the curve, not overlapping the cards. Also trim the empty space under the
illustration (fit the viewBox height to the content). When finished, list the file you
changed and stop.
