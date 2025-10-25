/**
 * App Component - Refactored
 * Clean application entry point using contexts and modular components
 * 
 * Before: 843 lines of mixed concerns
 * After: 25 lines of clean architecture
 */

import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { AppLayout } from './layouts/AppLayout';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
