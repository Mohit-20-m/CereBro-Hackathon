/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Palette
        sky: '#99CDD8',
        mint: '#DAEBE3',
        cream: '#FDE8D3',
        blush: '#F3C3B2',
        sage: '#CFD6C4',
        moss: '#657166',
        // Derived from the palette for text + warnings
        ink: '#2C362E',
        coral: '#A34630',
        amber: '#D9A441',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['"Bricolage Grotesque"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        pop: {
          '0%': { opacity: '0', transform: 'translateY(8px) scale(0.96)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(32px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        dot: {
          '0%, 80%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '40%': { transform: 'translateY(-4px)', opacity: '1' },
        },
        nodeIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        pop: 'pop 0.35s cubic-bezier(0.22, 1, 0.36, 1)',
        slideIn: 'slideIn 0.4s cubic-bezier(0.22, 1, 0.36, 1)',
        fadeIn: 'fadeIn 0.3s ease-out',
        dot: 'dot 1.2s infinite ease-in-out',
        nodeIn: 'nodeIn 0.4s ease-out both',
      },
    },
  },
  plugins: [],
}
