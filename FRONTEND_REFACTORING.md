# Frontend Refactoring Plan

## Overview

Refactoring the React frontend from a monolithic `App.tsx` (843 lines) into a clean, modular architecture following React best practices.

## Current Issues

- **App.tsx**: 843 lines - too much responsibility
- Mixed concerns: auth, theme, UI, business logic
- No separation of concerns
- Hard to test individual features
- Difficult to reuse components

## New Structure

```
frontend/src/
├── config/
│   └── constants.ts          # App-wide constants
├── contexts/
│   ├── AuthContext.tsx        # Auth state & logic
│   └── ThemeContext.tsx       # Theme state & logic
├── hooks/
│   ├── useAuth.ts             # Auth hook
│   ├── useTheme.ts            # Theme hook
│   ├── useLocalStorage.ts    # LocalStorage hook
│   └── useWebSocket.ts        # WebSocket hook
├── services/
│   └── api/
│       ├── auth.service.ts    # Auth API calls
│       ├── search.service.ts  # Search API calls
│       ├── chat.service.ts    # Chat API calls
│       └── news.service.ts    # News API calls
├── layouts/
│   ├── AppLayout.tsx          # Main layout wrapper
│   ├── Header.tsx             # App header
│   └── UserMenu.tsx           # User dropdown menu
├── features/
│   ├── auth/
│   │   ├── components/
│   │   │   ├── AuthDialog.tsx
│   │   │   ├── LoginForm.tsx
│   │   │   └── VerificationForm.tsx
│   │   └── index.ts
│   ├── chat/
│   │   ├── CommunityChat.tsx  # Existing
│   │   └── components/...     # Existing
│   ├── news/
│   │   ├── AINews.tsx         # Existing
│   │   └── index.ts
│   └── topics/
│       ├── TopicsHome.tsx     # Existing
│       └── index.ts
└── App.tsx                     # Clean routing & providers
```

## Key Improvements

### 1. Separation of Concerns ✅
- **Contexts**: Global state management
- **Hooks**: Reusable logic
- **Services**: API communication
- **Features**: Domain-specific code
- **Layouts**: UI structure

### 2. Context API for State Management
- `AuthContext`: User authentication, session management
- `ThemeContext`: Dark mode, theme switching

### 3. Custom Hooks
- `useAuth()`: Auth operations (login, logout, session)
- `useTheme()`: Theme operations (toggle, persist)
- `useLocalStorage()`: Generic local storage hook
- `useWebSocket()`: WebSocket connection management

### 4. Service Layer
- Clean API abstraction
- Single responsibility per service
- Easy to mock for testing
- Centralized error handling

### 5. Feature Modules
- Self-contained feature directories
- Components, logic, types in one place
- Easy to understand and maintain

## Before vs After

### Before (Monolithic)
```tsx
// App.tsx - 843 lines
function App() {
  // Auth state (50+ lines)
  const [userProfile, setUserProfile] = useState(...);
  const [authStep, setAuthStep] = useState(...);
  // ... many more state variables
  
  // Auth functions (100+ lines)
  const handleRequestCode = async () => { ... };
  const handleVerifyCode = async () => { ... };
  // ... many more functions
  
  // Theme logic (20+ lines)
  const [darkMode, setDarkMode] = useState(...);
  const toggleDarkMode = () => { ... };
  
  // Render logic (600+ lines)
  return (
    // Everything mixed together
  );
}
```

### After (Modular)
```tsx
// App.tsx - ~100 lines
function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppLayout>
          <Routes />
        </AppLayout>
      </AuthProvider>
    </ThemeProvider>
  );
}

// Usage in components
function SomeFeature() {
  const { user, login, logout } = useAuth();
  const { darkMode, toggle } = useTheme();
  // Clean, focused component
}
```

## Benefits

✅ **Maintainability**: Each file has a single, clear purpose  
✅ **Testability**: Easy to unit test hooks and services  
✅ **Reusability**: Hooks and services can be used anywhere  
✅ **Scalability**: Easy to add new features  
✅ **Developer Experience**: Better IntelliSense and navigation  
✅ **Performance**: Can optimize re-renders with contexts  
✅ **Code Organization**: Related code grouped together  

## Migration Strategy

1. ✅ Create directory structure
2. ✅ Extract constants
3. ✅ Create service layer
4. ✅ Create contexts (Auth, Theme)
5. ✅ Create custom hooks
6. ✅ Extract layout components
7. ✅ Extract auth components
8. ✅ Refactor App.tsx
9. ✅ Test all functionality
10. ✅ Update documentation

## No Breaking Changes

- All existing components work as-is
- Backend API unchanged
- User experience identical
- Gradual migration possible

## Testing Plan

After refactoring:
1. Build frontend: `npm run build`
2. Test auth flow
3. Test theme switching
4. Test chat functionality
5. Test news feed
6. Test topics navigation

## File Size Comparison

| File | Before | After |
|------|--------|-------|
| App.tsx | 843 lines | ~100 lines |
| Total LOC | ~843 | ~1200 (distributed across modules) |
| Complexity | High | Low (per file) |

## Next Steps

1. Implement contexts
2. Create custom hooks
3. Extract components
4. Refactor App.tsx
5. Test thoroughly
6. Document changes

---

**Goal**: Clean, maintainable, scalable React architecture following industry best practices.
