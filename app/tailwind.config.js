/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./frontend/index.html",
    "./frontend/src/**/*.{ts,tsx,js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
        score: {
          ready: "#22c55e",
          mostly: "#84cc16",
          work: "#f59e0b",
          notready: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};
