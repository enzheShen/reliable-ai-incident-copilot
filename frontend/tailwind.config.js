/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#13211c',
        canvas: '#f3f5ef',
        signal: '#d95d39',
        moss: '#275d4a',
      },
      boxShadow: { card: '0 20px 45px -30px rgba(19, 33, 28, 0.42)' },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        display: ['Georgia', 'ui-serif', 'serif'],
      },
    },
  },
  plugins: [],
}
