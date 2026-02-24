/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#05060a",
        brand: {
          red: "#dc2626",
          "red-dark": "#991b1b",
          "red-light": "#ef4444",
        },
        surface: {
          DEFAULT: "#0c0d12",
          raised: "#13141c",
          overlay: "#1a1c26",
          border: "#2a2d3a",
        },
        steel: "#7a8194",
        accent: "#dc2626",
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["DM Sans", "system-ui", "sans-serif"],
        sans: ["DM Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "Fira Code", "monospace"],
      },
      keyframes: {
        fadeSlideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        barFill: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 4px rgba(220, 38, 38, 0.3)" },
          "50%": { boxShadow: "0 0 12px rgba(220, 38, 38, 0.6)" },
        },
      },
      animation: {
        "slide-up": "fadeSlideUp 0.4s ease-out both",
        "bar-fill": "barFill 0.6s ease-out both",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
