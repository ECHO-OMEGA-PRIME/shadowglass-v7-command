import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        ept: {
          dark: '#050508',
          darker: '#020204',
          accent: '#0d7377',
          'accent-light': '#14b8a6',
          'accent-glow': '#0fa4a8',
          slate: '#94a3b8',
          muted: '#64748b',
          border: '#1e293b',
          surface: '#0f172a',
          'surface-light': '#1e293b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
export default config;
