import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box, Avatar, Menu, MenuItem } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';

export default function Header({ user, onMenuClick }) {
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  return (
    <AppBar position="sticky" sx={{ backgroundColor: '#ffffff', color: '#1e1e2d', boxShadow: 1 }}>
      <Toolbar>
        <IconButton edge="start" color="inherit" onClick={onMenuClick} sx={{ mr: 2 }}>
          <MenuIcon />
        </IconButton>

        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Sistema de Gestión de Horarios
        </Typography>

        <Box sx={{ textAlign: 'right', mr: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {user?.full_name || user?.name || 'Usuario'}
          </Typography>
          <Typography variant="caption" sx={{ color: '#666' }}>
            {user?.role || 'Rol'}
          </Typography>
        </Box>

        <IconButton onClick={handleMenu}>
          <Avatar sx={{ width: 40, height: 40, backgroundColor: '#1976d2' }}>
            <AccountCircleIcon />
          </Avatar>
        </IconButton>

        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleClose}
        >
          <MenuItem onClick={handleClose}>Mi Perfil</MenuItem>
          <MenuItem onClick={handleLogout}>Cerrar Sesión</MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
