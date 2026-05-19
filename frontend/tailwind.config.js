/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#ecfdf5',
          100: '#d1fae5',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"DM Mono"', 'ui-monospace', 'monospace'],
      },
      backgroundImage: {
        'grid-faint': `linear-gradient(rgba(16,185,129,0.03) 1px, transparent 1px),
                       linear-gradient(90deg, rgba(16,185,129,0.03) 1px, transparent 1px)`,
      },
      backgroundSize: {
        'grid-faint': '32px 32px',
      },
    },
  },
  plugins: [],
};
