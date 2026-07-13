import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "var(--font-geist-sans)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        background: "var(--background)",
        surface: {
          DEFAULT: "var(--surface)",
          deep: "var(--surface-deep)",
        },
        edge: "var(--border)",
        ink: "var(--foreground)",
        muted: "var(--muted)",
        pos: {
          DEFAULT: "var(--teal)",
          bright: "var(--teal-bright)",
          text: "var(--teal-text)",
        },
        neg: {
          DEFAULT: "var(--coral)",
          text: "var(--coral-text)",
        },
        warn: {
          DEFAULT: "var(--amber)",
          text: "var(--amber-text)",
        },
        seriesb: "var(--violet)",
      },
    },
  },
  plugins: [],
};
export default config;
