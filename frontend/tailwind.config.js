/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dp-dark': {
          50: '#1a1d23',
          100: '#14161a',
          200: '#0f1114',
          300: '#0a0c0e',
        },
        'dp-accent': {
          DEFAULT: '#10b981',
          light: '#34d399',
          dark: '#059669',
        }
      }
    },
  },
  plugins: [],
}
