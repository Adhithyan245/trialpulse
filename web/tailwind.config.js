/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        surface: "var(--surface)",
        card: "var(--card)",
        line: "var(--line)",
        text: "var(--text)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        pass: "var(--pass)",
        "pass-soft": "var(--pass-soft)",
        watch: "var(--watch)",
        "watch-soft": "var(--watch-soft)",
        held: "var(--held)",
        "held-soft": "var(--held-soft)",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
