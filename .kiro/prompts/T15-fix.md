Task T15-fix: one type error after PublicMetrics was introduced.

You cannot run shell commands or use the web in this project; the reviewer builds it.
Files you may edit: web/src/scenes/Scene1Trial.tsx and files in web/src/scenes/trial/.

  src/scenes/Scene1Trial.tsx(153,19): error TS2322: Type 'PublicMetrics | null' is not
  assignable to type 'Record<string, unknown> | null'.
web/src/types.ts now exports PublicMetrics (with short_sleep_by_county:
Record<string, number>). Change the receiving prop/state types in Scene 1 to use
PublicMetrics (import it from ../types or ../../types) and read
short_sleep_by_county from it directly; no `any`. When finished, list the files you
changed and stop.
