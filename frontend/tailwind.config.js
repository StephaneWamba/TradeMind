/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Background colors - Refined darker palette
        bg: {
          primary: '#0f1419',      // Slightly lighter for better contrast
          secondary: '#131722',    // Secondary areas
          card: '#1e222d',         // Card background
          elevated: '#252932',     // Elevated elements
          hover: '#2a2e3a',        // Hover states
          glow: 'rgba(59, 130, 246, 0.1)', // Subtle glow effect
        },
        // Accent colors - More vibrant trading colors
        accent: {
          primary: '#3b82f6',      // Brighter blue (primary actions)
          secondary: '#2563eb',    // Secondary blue
          success: '#00d4aa',      // More vibrant green for profits
          danger: '#ff4757',       // More prominent red for losses
          warning: '#ffa726',      // Orange for warnings
          info: '#42a5f5',         // Info blue
        },
        // Text colors - Enhanced contrast
        text: {
          primary: '#ffffff',      // Pure white for primary text
          secondary: '#cbd5e1',    // Better contrast gray
          muted: '#94a3b8',        // Muted gray
          disabled: '#64748b',     // Disabled text
        },
        // Border colors
        border: {
          default: '#2a2e39',     // Default borders
          active: '#3b82f6',      // Active border
          divider: '#363a45',     // Dividers
          hover: '#3a3e4a',       // Hover borders
          glow: 'rgba(59, 130, 246, 0.3)', // Glow border
        },
        // Chart colors
        chart: {
          up: '#00d4aa',          // Vibrant green for up candles/positive
          down: '#ff4757',         // Prominent red for down candles/negative
          grid: '#1a1e2a',        // Darker grid lines
          axis: '#94a3b8',         // Better contrast axis text
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        lg: '8px',
        md: '6px',
        sm: '4px',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
        'glow': '0 0 20px rgba(59, 130, 246, 0.4)',
        'glow-success': '0 0 20px rgba(0, 212, 170, 0.3)',
        'glow-danger': '0 0 20px rgba(255, 71, 87, 0.3)',
        'inner': 'inset 0 2px 4px rgba(0, 0, 0, 0.3)',
      },
      maxWidth: {
        'page': '1600px',  // Max width for page content
        'content': '1400px', // Max width for main content
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-in',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}


