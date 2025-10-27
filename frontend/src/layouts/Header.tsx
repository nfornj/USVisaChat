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
  useMediaQuery,
  useTheme as useMuiTheme,
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

// Subtle text shimmer animation for AI News text
const textShimmer = keyframes`
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
  const muiTheme = useMuiTheme();
  const isMobile = useMediaQuery(muiTheme.breakpoints.down('sm'));

  return (
    <AppBar 
      position="static" 
      elevation={0} 
      sx={{ 
        bgcolor: 'primary.main',
        borderBottom: 1, 
        borderColor: 'divider' 
      }}
    >
      <Toolbar sx={{ minHeight: isMobile ? 56 : 64, px: { xs: 1, sm: 2 } }}>
        {/* Logo */}
        <Avatar
          sx={{
            width: isMobile ? 32 : UI_CONFIG.AVATAR_SIZE.SMALL,
            height: isMobile ? 32 : UI_CONFIG.AVATAR_SIZE.SMALL,
            mr: { xs: 1, sm: 2 },
            background: 'linear-gradient(135deg, #7c3aed 0%, #ec4899 100%)',
          }}
        >
          <GroupsIcon sx={{ fontSize: isMobile ? 20 : 24 }} />
        </Avatar>
        <Typography 
          variant={isMobile ? 'body1' : 'h6'} 
          component="div" 
          fontWeight="bold"
          sx={{ 
            fontSize: { xs: '0.9rem', sm: '1.25rem' },
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: { xs: '120px', sm: 'none' }
          }}
        >
          {isMobile ? 'H1B Visa' : APP_NAME}
        </Typography>

        <Box sx={{ flexGrow: 1 }} />

        {/* Topics Button */}
        <Chip
          icon={!isMobile ? <GroupsIcon /> : undefined}
          label={isMobile ? 'Topics' : 'Topics'}
          size={isMobile ? 'small' : 'medium'}
          sx={{
            fontWeight: 600,
            mr: { xs: 0.5, sm: 2 },
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            border: '1px solid',
            fontSize: { xs: '0.75rem', sm: '0.875rem' },
            height: { xs: 28, sm: 32 },
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

        {/* AI News Button */}
        <Chip
          icon={!isMobile ? <ArticleIcon /> : undefined}
          label={isMobile ? 'News' : 'AI News'}
          size={isMobile ? 'small' : 'medium'}
          sx={{
            fontWeight: 600,
            mr: { xs: 0.5, sm: 2 },
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            border: '1px solid',
            fontSize: { xs: '0.75rem', sm: '0.875rem' },
            height: { xs: 28, sm: 32 },
            position: 'relative',
            '& .MuiChip-label': activeTab === 'news' ? {
              background: 'linear-gradient(90deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,1) 50%, rgba(255,255,255,0.8) 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundSize: '200% auto',
              animation: `${textShimmer} 3s linear infinite`,
            } : undefined,
            ...(activeTab === 'news'
              ? {
                  bgcolor: 'rgba(255, 255, 255, 0.3)',
                  borderColor: 'rgba(255, 255, 255, 0.4)',
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
          onClick={() => onTabChange('news')}
        />

        {/* User Menu */}
        <UserMenu />

        {/* Theme Toggle */}
        {!isMobile && (
          <IconButton 
            onClick={toggleTheme} 
            sx={{ ml: { xs: 0.5, sm: 1 } }}
            size={isMobile ? 'small' : 'medium'}
          >
            {darkMode ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
          </IconButton>
        )}
      </Toolbar>
    </AppBar>
  );
}
