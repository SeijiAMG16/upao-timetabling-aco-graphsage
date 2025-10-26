import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Divider, Typography, Box } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SchoolIcon from '@mui/icons-material/School';
import UploadIcon from '@mui/icons-material/Upload';
import GridOnIcon from '@mui/icons-material/GridOn';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import ScheduleIcon from '@mui/icons-material/Schedule';

const DRAWER_WIDTH = 280;

export default function Sidebar({ open }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: open ? DRAWER_WIDTH : 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          backgroundColor: '#1e1e2d',
          color: '#ffffff',
        },
      }}
    >
      <Box sx={{ p: 2, backgroundColor: '#151521', display: 'flex', alignItems: 'center', gap: 1 }}>
        <SchoolIcon sx={{ fontSize: 32, color: '#1976d2' }} />
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>UPAO Timetabling</Typography>
          <Typography variant="caption" sx={{ color: '#a0a0a0' }}>Sistema de Horarios</Typography>
        </Box>
      </Box>

      <Divider sx={{ backgroundColor: '#2d2d3d' }} />

      <List sx={{ mt: 2 }}>
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/dashboard')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/dashboard' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <DashboardIcon />
            </ListItemIcon>
            <ListItemText primary="Dashboard" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/generar-horario')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/generar-horario' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <ScheduleIcon />
            </ListItemIcon>
            <ListItemText primary="Generar Horario" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/projections')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/projections' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <SchoolIcon />
            </ListItemIcon>
            <ListItemText primary="Proyecciones" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/professors')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/professors' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <SchoolIcon />
            </ListItemIcon>
            <ListItemText primary="Profesores" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/professor-assignments')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/professor-assignments' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <PersonAddAltIcon />
            </ListItemIcon>
            <ListItemText primary="Asignaciones" />
          </ListItemButton>
        </ListItem>

        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/professors-upload')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/professors-upload' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <UploadIcon />
            </ListItemIcon>
            <ListItemText primary="Upload Profesores" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/restrictions')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/restrictions' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <GridOnIcon />
            </ListItemIcon>
            <ListItemText primary="Restricciones Profesores" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/courses')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/courses' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <SchoolIcon />
            </ListItemIcon>
            <ListItemText primary="Cursos" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton 
            onClick={() => navigate('/classrooms')}
            sx={{ 
              mx: 1, 
              borderRadius: 1, 
              backgroundColor: location.pathname === '/classrooms' ? '#1976d2' : 'transparent' 
            }}
          >
            <ListItemIcon sx={{ color: '#ffffff', minWidth: 45 }}>
              <SchoolIcon />
            </ListItemIcon>
            <ListItemText primary="Aulas" />
          </ListItemButton>
        </ListItem>
      </List>

      <Box sx={{ flexGrow: 1 }} />
      <Box sx={{ p: 2, backgroundColor: '#151521' }}>
        <Typography variant="caption" sx={{ color: '#707070', textAlign: 'center', display: 'block' }}>
          ISIA - UPAO © 2025
        </Typography>
      </Box>
    </Drawer>
  );
}
