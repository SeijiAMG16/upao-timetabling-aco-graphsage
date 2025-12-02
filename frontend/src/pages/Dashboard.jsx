import React, { useState, useEffect } from 'react';
import { Box, Grid, Paper, Typography, CircularProgress, Card, CardContent } from '@mui/material';
import PeopleIcon from '@mui/icons-material/People';
import SchoolIcon from '@mui/icons-material/School';
import MeetingRoomIcon from '@mui/icons-material/MeetingRoom';
import BlockIcon from '@mui/icons-material/Block';
import axios from 'axios';

const API_BASE = `${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api`;

export default function Dashboard() {
  const [stats, setStats] = useState({ professors: 0, courses: 0, classrooms: 0, restrictions: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [profRes, coursesRes, classroomsRes, restrictionsRes] = await Promise.all([
        axios.get(`${API_BASE}/professors`), 
        axios.get(`${API_BASE}/projections/courses`),
        axios.get(`${API_BASE}/classrooms`), 
        axios.get(`${API_BASE}/assignments/restrictions`)
      ]);
      setStats({ 
        professors: profRes.data.total || 0, 
        courses: coursesRes.data.total || 0,
        classrooms: classroomsRes.data.total || 0, 
        restrictions: restrictionsRes.data.restrictions?.length || 0 
      });
    } catch (error) { 
      console.error('Error fetching dashboard stats:', error); 
    } finally { 
      setLoading(false); 
    }
  };

  const StatCard = ({ title, value, icon, color }) => (
    <Card sx={{ height: '100%' }}><CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Box><Typography variant="h4" sx={{ fontWeight: 700 }}>{loading ? <CircularProgress size={30} /> : value}</Typography>
          <Typography variant="body2" color="text.secondary">{title}</Typography></Box>
        <Box sx={{ width: 56, height: 56, borderRadius: 2, backgroundColor: color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{icon}</Box>
      </Box></CardContent></Card>
  );

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>Dashboard General</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}><StatCard title="Profesores Activos" value={stats.professors} icon={<PeopleIcon sx={{ fontSize: 32, color: '#1976d2' }} />} color="#e3f2fd" /></Grid>
        <Grid item xs={12} sm={6} md={3}><StatCard title="Cursos Registrados" value={stats.courses} icon={<SchoolIcon sx={{ fontSize: 32, color: '#4caf50' }} />} color="#e8f5e9" /></Grid>
        <Grid item xs={12} sm={6} md={3}><StatCard title="Aulas Disponibles" value={stats.classrooms} icon={<MeetingRoomIcon sx={{ fontSize: 32, color: '#ff9800' }} />} color="#fff3e0" /></Grid>
        <Grid item xs={12} sm={6} md={3}><StatCard title="Restricciones Activas" value={stats.restrictions} icon={<BlockIcon sx={{ fontSize: 32, color: '#e91e63' }} />} color="#fce4ec" /></Grid>
      </Grid>
      <Paper sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}> Sistema Completo Funcional</Typography>
        <Typography variant="body2" color="text.secondary">Autenticación JWT, CRUD completo, Upload Excel, Dashboard en tiempo real</Typography>
      </Paper>
    </Box>
  );
}
