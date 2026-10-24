Task T16-fix: TypeScript errors in Scenes 4 and 5.

You cannot run shell commands or use the web in this project; the reviewer builds it.
Files you may edit: web/src/scenes/Scene4Verified.tsx, web/src/scenes/Scene5Proof.tsx,
web/src/types.ts (add or tighten types only). Nothing else.

`npm run build` fails with:
  src/scenes/Scene4Verified.tsx(4,33): error TS6196: 'Reading' is declared but never used.
  src/scenes/Scene5Proof.tsx(200,49): error TS2339: Property 'find' does not exist on type '{}'.
  src/scenes/Scene5Proof.tsx(201,54): error TS2339: Property 'find' does not exist on type '{}'.
  src/scenes/Scene5Proof.tsx(209,13): error TS2322: Type '{}' is not assignable to type 'ReactNode'.
  src/scenes/Scene5Proof.tsx(216,13): error TS2322: Type '{}' is not assignable to type 'ReactNode'.
  src/scenes/Scene5Proof.tsx(223,13): error TS2322: Type '{}' is not assignable to type 'ReactNode'.
The public metrics object is typed too loosely. Its real shape (data/derived/
metrics_public.json): total_trials: number; by_phase: Record<string, number>;
wearable_measurable_trials: number; trials_with_ma_city: number; top_cities:
Array<[string, number]>; ej_block_groups: number; ej_municipalities: number;
trials_in_ej_municipalities: number; short_sleep_by_county: Record<string, number>;
readmissions: { hospitals: number; measures: Record<string, { with_ratio: number;
above_1: number }>; heart_failure_above_1: number }. Define PublicMetrics with exactly
this in types.ts, type the metrics response with it, and fix the code to use it (no `any`,
no casts to `{}`). Remove the unused import. When finished, list the files you changed
and stop.
