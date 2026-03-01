import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        panel: "var(--panel)",
        panelSoft: "var(--panel-soft)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        accentSoft: "var(--accent-soft)",
        low: "var(--low)",
        moderate: "var(--moderate)",
        high: "var(--high)",
        border: "var(--border)",
        danger: "var(--danger)",
        hazardLandfill: "var(--haz-landfill)",
        hazardLandfillSoft: "var(--haz-landfill-soft)",
        hazardMilitary: "var(--haz-military)",
        hazardMilitarySoft: "var(--haz-military-soft)",
        hazardIndustrial: "var(--haz-industrial)",
        hazardIndustrialSoft: "var(--haz-industrial-soft)",
        hazardSuperfund: "var(--haz-superfund)",
        hazardSuperfundSoft: "var(--haz-superfund-soft)",
      },
      boxShadow: {
        panel: "0 20px 50px rgba(8, 16, 30, 0.26)",
      },
      keyframes: {
        revealUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        revealUp: "revealUp 500ms ease forwards",
      },
    },
  },
  plugins: [],
};

export default config;
