/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./template/**/*.html",
    "./mytask/templates/**/*.html",
    "./customadmin/templates/**/*.html",
    "./login_page.html",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#383838',
        'primary-dark': '#2a2a2a',
        secondary: '#696969',
        accent: '#c9adb7',
        'accent-light': '#d5c8d3',
        navy: '#383838',
        'navy-light': '#696969',
        // Gradient colors
        'gradient-pink': '#cdb5bd',
        'gradient-purple': '#c9adb7',
        'gradient-blue': '#8d9fcf',
        'gradient-light': '#d5c8d3',
        'gradient-soft': '#cbb2bb',
        'accent-black': '#3c3c3c',
        'bg-light': '#d4d4d6',
        'border-gray': '#c8bdc4',
      },
      fontFamily: {
        sans: ['Poppins', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        display: ['Poppins', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        poppins: ['Poppins', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 2px 6px rgba(0, 0, 0, 0.06)',
        'card': '0 14px 28px rgba(0, 0, 0, 0.10)',
        'glow': '0 24px 42px rgba(0, 0, 0, 0.18)',
        'glow-sm': '0 14px 26px rgba(0, 0, 0, 0.14)',
        'colored': '0 24px 42px rgba(0, 0, 0, 0.18)',
        'gradient': '0 10px 30px rgba(201, 173, 183, 0.15)',
        'gradient-lg': '0 20px 45px rgba(201, 173, 183, 0.20)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'fade-in-up': 'fadeInUp 0.6s ease-out',
        'slide-in-right': 'slideInRight 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 3s ease-in-out infinite',
        'gradient-shift': 'gradientShift 8s ease infinite',
        'gradient-flow': 'gradientFlow 6s ease infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(-20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        gradientFlow: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '50%': { opacity: '1' },
          '100%': { transform: 'translateX(100%)', opacity: '0' },
        },
      },
      backgroundSize: {
        '200%': '200% 200%',
      },
    },
  },
  plugins: [],
}