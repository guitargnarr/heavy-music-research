/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          red: "#dc2626",
          "red-dark": "#991b1b",
          "red-light": "#ef4444",
        },
        surface: {
          DEFAULT: "#0f0f0f",
          raised: "#1a1a1a",
          overlay: "#242424",
          border: "#333333",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
