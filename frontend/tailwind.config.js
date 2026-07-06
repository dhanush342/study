/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        atlas: {
          bg: '#0F172A',
          surface: '#1E293B',
          border: '#334155',
          text: '#F8FAFC',
          muted: '#94A3B8',
        },
        brand: {
          400: '#FB923C',
          500: '#F97316',
          600: '#EA580C',
        },
      },
      animation: {
        'slide-in-left': 'slideInLeft 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        slideInLeft: {
          from: { transform: 'translateX(-100%)', opacity: 0 },
          to: { transform: 'translateX(0)', opacity: 1 },
        },
        slideInRight: {
          from: { transform: 'translateX(100%)', opacity: 0 },
          to: { transform: 'translateX(0)', opacity: 1 },
        },
        fadeIn: {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}
