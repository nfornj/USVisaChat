import { createTheme, ThemeOptions } from '@mui/material/styles';

// Custom color palette
const getDesignTokens = (mode: 'light' | 'dark'): ThemeOptions => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          // Light mode - Purple Community Theme
          primary: {
            main: '#7c3aed', // Vibrant purple
            light: '#a78bfa',
            dark: '#6d28d9',
            contrastText: '#fff',
          },
          secondary: {
            main: '#ec4899', // Pink accent for important actions
            light: '#f472b6',
            dark: '#db2777',
            contrastText: '#fff',
          },
          background: {
            default: '#faf5ff', // Very light purple tint
            paper: '#ffffff',
          },
          text: {
            primary: '#1e1b4b', // Deep indigo
            secondary: '#6b7280', // Neutral gray
          },
          success: {
            main: '#10b981', // Emerald green
            light: '#34d399',
            dark: '#059669',
          },
          error: {
            main: '#ef4444', // Red
            light: '#f87171',
            dark: '#dc2626',
          },
          warning: {
            main: '#f59e0b', // Amber
            light: '#fbbf24',
            dark: '#d97706',
          },
          info: {
            main: '#8b5cf6', // Purple info
            light: '#a78bfa',
            dark: '#7c3aed',
          },
        }
      : {
          // Dark mode - Purple Theme
          primary: {
            main: '#a78bfa', // Lighter purple for dark mode
            light: '#c4b5fd',
            dark: '#8b5cf6',
            contrastText: '#1e1b4b',
          },
          secondary: {
            main: '#f472b6', // Lighter pink for dark mode
            light: '#f9a8d4',
            dark: '#ec4899',
            contrastText: '#1e1b4b',
          },
          background: {
            default: '#0f172a',
            paper: '#1e293b',
          },
          text: {
            primary: '#f8fafc',
            secondary: '#cbd5e1',
          },
          success: {
            main: '#34d399', // Emerald
            light: '#6ee7b7',
            dark: '#10b981',
          },
          error: {
            main: '#f87171', // Red
            light: '#fca5a5',
            dark: '#ef4444',
          },
          warning: {
            main: '#fbbf24', // Amber
            light: '#fcd34d',
            dark: '#f59e0b',
          },
          info: {
            main: '#c4b5fd', // Lighter purple info
            light: '#ddd6fe',
            dark: '#a78bfa',
          },
        }),
  },
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
      lineHeight: 1.2,
    },
    h2: {
      fontWeight: 700,
      fontSize: '2rem',
      lineHeight: 1.3,
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.75rem',
      lineHeight: 1.4,
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.4,
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.5,
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 0,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          padding: '10px 24px',
          fontSize: '0.95rem',
          fontWeight: 500,
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        contained: {
          '&:hover': {
            transform: 'translateY(-1px)',
            transition: 'transform 0.2s',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          boxShadow: mode === 'dark' 
            ? '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)'
            : '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          borderRadius: 0,
        },
        rounded: {
          borderRadius: 0,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 0,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 0,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 0,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 0,
        },
      },
    },
  },
});

export const createAppTheme = (mode: 'light' | 'dark') => {
  return createTheme(getDesignTokens(mode));
};

export default createAppTheme;

