import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Space Grotesk'", "sans-serif"]
      },
      colors: {
        ink: "#0f172a",
        fog: "#e2e8f0",
        dusk: "#0b1324",
        mint: "#14b8a6",
        amber: "#f59e0b",
        crimson: "#ef4444"
      }
    }
  },
  plugins: []
};

export default config;