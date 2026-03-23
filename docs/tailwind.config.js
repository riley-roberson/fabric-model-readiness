/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#1B365D",
          teal: "#5F8A8B",
          emerald: {
            DEFAULT: "#00A77F",
            light: "#1DB892",
          },
          berry: {
            DEFAULT: "#AD3459",
            light: "#C94B72",
          },
        },
      },
    },
  },
  plugins: [],
};
