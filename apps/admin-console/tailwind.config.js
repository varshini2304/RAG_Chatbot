/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0c15",
        surface: "#121324",
        border: "#1f213a",
        muted: "#94a3b8",
        primary: {
          DEFAULT: "#6366f1",
          hover: "#4f46e5",
          dark: "#4338ca",
        },
        accent: {
          purple: "#a855f7",
          purpleDark: "#7c3aed",
        },
        success: "#22c55e",
        warning: "#fbbf24",
        danger: "#ef4444",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        outfit: ["Outfit", "sans-serif"],
      },
    },
  },
  plugins: [],
}
