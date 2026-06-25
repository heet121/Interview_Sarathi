/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // base (dark "compiler" canvas)
        bg:      '#0b0b0e',
        ink:     '#0b0b0e',
        s1:      '#141419',
        s2:      '#1b1b22',
        s3:      '#26262f',
        panel:   '#141419',
        // structure
        line:    '#2b2b35',
        lineHi:  '#3a3a47',
        paper:   '#f4f3ec',
        border:  '#2b2b35',
        // accents (syntax-highlight palette)
        acid:    '#a3e635',
        acid2:   '#bef264',
        gold:    '#e8c547',   // kept for backward-compat with un-migrated pages
        teal:    '#2dd4bf',
        cyan:    '#22d3ee',
        violet:  '#a78bfa',
        pink:    '#f472b6',
        // semantic
        ok:      '#4ade80',
        warn:    '#fbbf24',
        bad:     '#f87171',
        // text
        muted:   '#9a9ab8',
        muted2:  '#6a6a80',
      },
      fontFamily: {
        sans:    ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        // remap serif -> grotesk so legacy `font-serif` usages stay on-brand
        serif:   ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        brutal:    '4px 4px 0 0 #0b0b0e',
        brutalLg:  '7px 7px 0 0 #0b0b0e',
        brutalW:   '4px 4px 0 0 #f4f3ec',
        brutalA:   '5px 5px 0 0 #a3e635',
        brutalAlg: '8px 8px 0 0 #a3e635',
      },
      animation: {
        'pulse-slow': 'pulse 2s ease-in-out infinite',
        'fade-up':    'fadeUp 0.4s ease both',
        'spin-slow':  'spin 3s linear infinite',
        blink:        'blink 1.1s steps(1) infinite',
        marquee:      'marquee 26s linear infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%,49%':   { opacity: '1' },
          '50%,100%': { opacity: '0' },
        },
        marquee: {
          from: { transform: 'translateX(0)' },
          to:   { transform: 'translateX(-50%)' },
        },
      },
    },
  },
  plugins: [],
}
