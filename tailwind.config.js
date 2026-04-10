/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:      '#08080f',
        s1:      '#0f0f1a',
        s2:      '#161625',
        s3:      '#1e1e30',
        gold:    '#e8c547',
        gold2:   '#f0d060',
        teal:    '#2dd4bf',
        muted:   '#9a9ab8',
        muted2:  '#6a6a88',
        border:  'rgba(255,255,255,0.06)',
      },
      fontFamily: {
        sans:  ['Geist', 'sans-serif'],
        serif: ['Instrument Serif', 'serif'],
        mono:  ['Geist Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s ease-in-out infinite',
        'fade-up':    'fadeUp 0.4s ease both',
        'spin-slow':  'spin 3s linear infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
