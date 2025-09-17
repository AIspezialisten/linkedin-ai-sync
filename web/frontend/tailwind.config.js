/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        linkedin: {
          50: '#eff8ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#0a66c2',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        confidence: {
          high: '#10b981',
          medium: '#f59e0b',
          low: '#ef4444',
          none: '#6b7280'
        }
      }
    },
  },
  plugins: [],
}