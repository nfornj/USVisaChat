/**
 * Header Component
 * Application header with navigation and user menu
 */

import {
  AppBar,
  Toolbar,
  Typography,
  Avatar,
  Box,
  Chip,
  IconButton,
  keyframes,
} from '@mui/material';
import {
  Groups as GroupsIcon,
  Article as ArticleIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
} from '@mui/icons-material';
import { useTheme } from '../contexts/ThemeContext';
import { UserMenu } from './UserMenu';
import { APP_NAME, UI_CONFIG } from '../config/constants';

// Subtle shine animation for Topics button
const subtleShine = keyframes`
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.85;
  }
`;

// Eye-catching shine animation for AI News button
const brightShine = keyframes`
  0% {
    background-position: -200% center;
  }
  100% {
    background-position: 200% center;
  }
`;

interface HeaderProps {
  activeTab: 'topics' | 'news';
  onTabChange: (tab: 'topics' | 'news') => void;
}

export function Header({ activeTab, onTabChange }: HeaderProps) {
  const { darkMode, toggleTheme } = useTheme();

  return (
    <AppBar 
      position="static" 
      elevation={0} 
      sx={{ 
        bgcolor: 'primary.main', // Match purple theme
        borderBottom: 1, 
        borderColor: 'divider' 
      }}
    >
      <Toolbar>
        {/* Logo */}
        <Avatar
          sx={{
            width: UI_CONFIG.AVATAR_SIZE.SMALL,
            height: UI_CONFIG.AVATAR_SIZE.SMALL,
            mr: 2,
            background: 'linear-gradient(135deg, #7c3aed 0%, #ec4899 100%)', // Purple to pink gradient
          }}
        >
          <GroupsIcon />
        </Avatar>
        <Typography variant="h6" component="div" fontWeight="bold">
          {APP_NAME}
        </Typography>

        <Box sx={{ flexGrow: 1 }} />

        {/* Topics Button */}
        <Chip
          icon={<GroupsIcon />}
          label="Topics"
          sx={{
            fontWeight: 600,
            mr: 2,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            border: '1px solid',
            ...(activeTab === 'topics'
              ? {
                  bgcolor: 'rgba(255, 255, 255, 0.3)',
                  borderColor: 'rgba(255, 255, 255, 0.4)',
                  color: '#fff',
                  boxShadow: '0 0 15px rgba(255, 255, 255, 0.2)',
                  animation: `${subtleShine} 3s ease-in-out infinite`,
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.35)',
                  },
                }
              : {
                  bgcolor: 'rgba(255, 255, 255, 0.2)',
                  borderColor: 'rgba(255, 255, 255, 0.3)',
                  color: '#fff',
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.25)',
                  },
                }),
          }}
          onClick={() => onTabChange('topics')}
        />

        {/* AI News Button - Always Animated */}
        <Chip
          icon={<ArticleIcon />}
          label="AI News"
          sx={{
            fontWeight: 600,
            mr: 2,
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            border: '2px solid',
            overflow: 'hidden',
            position: 'relative',
            // Always animate - regardless of active state
            background: 'linear-gradient(90deg, #ec4899 0%, #f472b6 50%, #ec4899 100%)',
            backgroundSize: '200% 100%',
            animation: `${brightShine} 2s linear infinite`,
            borderColor: '#fde047',
            color: '#fff',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: '-100%',
              width: '100%',
              height: '100%',
              background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent)',
              animation: `${brightShine} 2s linear infinite`,
            },
            ...(activeTab === 'news'
              ? {
                  boxShadow: '0 0 30px rgba(253, 224, 71, 0.5)',
                  '&:hover': {
                    boxShadow: '0 0 35px rgba(253, 224, 71, 0.6)',
                  },
                }
              : {
                  boxShadow: '0 0 20px rgba(253, 224, 71, 0.3)',
                  '&:hover': {
                    boxShadow: '0 0 25px rgba(253, 224, 71, 0.4)',
                  },
                }),
          }}
          onClick={() => onTabChange('news')}
        />

        {/* User Menu */}
        <UserMenu />

        {/* Theme Toggle */}
        <IconButton onClick={toggleTheme} sx={{ ml: 1 }}>
          {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}
