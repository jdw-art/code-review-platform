import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      spacing: {
        4.5: "1.125rem",
      },
      borderRadius: {
        xs: "0.25rem",
      },
      fontSize: {
        "2.5xl": ["2rem", { lineHeight: "2.5rem" }],
      },
      colors: {
        indigo: {
          55: "#f6f8ff",
          150: "#d6ddfe",
          505: "#6065f1",
          550: "#585bee",
          650: "#4338ca",
          750: "#3d34b6",
        },
        slate: {
          150: "#e8edf5",
          350: "#b4c0cf",
          450: "#7b8ca3",
          850: "#172033",
        },
      },
      boxShadow: {
        xs: "0 1px 2px rgba(15,23,42,0.03)",
        "2xs": "0 1px 2px rgba(15,23,42,0.04)",
        "3xs": "0 1px 1px rgba(15,23,42,0.04)",
      },
    }
  },
  plugins: []
} satisfies Config;
