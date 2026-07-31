/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#09090B',
          soft: '#0D0D11',
          card: '#111114',
        },
        primary: {
          DEFAULT: '#7C3AED',
          50: '#F3EBFF',
          400: '#9B6BFF',
          500: '#7C3AED',
          600: '#6B21D8',
        },
        secondary: {
          DEFAULT: '#4F46E5',
        },
        accent: {
          DEFAULT: '#06B6D4',
        },
        success: {
          DEFAULT: '#22C55E',
        },
        warning: {
          DEFAULT: '#F59E0B',
        },
        danger: {
          DEFAULT: '#EF4444',
        },
      },
      fontFamily: {
        display: ['"Outfit"', 'sans-serif'],
        sans: ['"Outfit"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backgroundImage: {
        'grid-glow':
          'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      boxShadow: {
        glow: '0 0 24px 0 rgba(124,58,237,0.45)',
        'glow-cyan': '0 0 24px 0 rgba(6,182,212,0.4)',
        'glow-danger': '0 0 24px 0 rgba(239,68,68,0.35)',
        card: '0 8px 40px -12px rgba(0,0,0,0.6)',
      },
      animation: {
        'blob-move': 'blob-move 18s ease-in-out infinite',
        'blob-move-2': 'blob-move-2 22s ease-in-out infinite',
        shimmer: 'shimmer 2.4s linear infinite',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-up': 'fade-up 0.6s ease forwards',
      },
      keyframes: {
        'blob-move': {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%': { transform: 'translate(60px, -40px) scale(1.15)' },
          '66%': { transform: 'translate(-40px, 30px) scale(0.95)' },
        },
        'blob-move-2': {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '50%': { transform: 'translate(-70px, 50px) scale(1.1)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(124,58,237,0.5)' },
          '70%': { boxShadow: '0 0 0 12px rgba(124,58,237,0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(124,58,237,0)' },
        },
        'fade-up': {
          '0%': { opacity: 0, transform: 'translateY(16px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
