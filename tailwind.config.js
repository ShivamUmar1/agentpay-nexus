/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#070B14',
        surface: '#0B1222',
        'surface-elevated': '#111C35',
        primary: {
          DEFAULT: '#00F0FF',
          dark: '#00B4D8',
          glow: 'rgba(0, 240, 255, 0.25)',
        },
        electric: '#0080FF',
        violet: {
          accent: '#8B5CF6',
          dark: '#6D28D9',
        },
        navy: {
          950: '#04070D',
          900: '#070B14',
          850: '#0B1222',
          800: '#111C35',
          700: '#1B2A4E',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 10px rgba(0, 240, 255, 0.3)' },
          '100%': { boxShadow: '0 0 25px rgba(0, 240, 255, 0.7)' },
        }
      }
    },
  },
  plugins: [],
}
