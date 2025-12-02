import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Button, Alert, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Select, MenuItem, FormControl, InputLabel, IconButton, Chip
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Block as BlockIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = `${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/assignments`;

const DAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const TIME_SLOTS = [
  '07:00', '07:50', '08:40', '09:40', '10:30', '11:20',
  '12:10', '13:00', '14:00', '14:50', '15:40', '16:30',
  '17:20', '18:20', '19:10', '20:00', '20:50', '21:40', '22:30'
];

export default function Restrictions() {
  const [restrictions, setRestrictions] = useState([]);
  const [professors, setProfessors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [formData, setFormData] = useState({
    professor_id: '',
    day: 'Lunes',
    start_time: '07:00',
    end_time: '08:40',
    reason: ''
  });

  useEffect(() => {
    fetchRestrictions();
    fetchProfessors();
  }, []);

  const fetchRestrictions = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/restrictions`);
      // Backend devuelve directamente el array de restricciones
      setRestrictions(response.data || []);
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al cargar restricciones' });
    } finally {
      setLoading(false);
    }
  };

  const fetchProfessors = async () => {
    try {
      // Endpoint correcto para profesores
      const API_PROFESSORS = `${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/professors`;
      const response = await axios.get(API_PROFESSORS);
      setProfessors(response.data.professors || []);
    } catch (error) {
      console.error('Error fetching professors');
    }
  };

  const handleOpenDialog = () => {
    setFormData({
      professor_id: '',
      day: 'Lunes',
      start_time: '07:00',
      end_time: '08:40',
      reason: ''
    });
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleSave = async () => {
    try {
      await axios.post(`${API_BASE}/restrictions`, formData);
      setMessage({ type: 'success', text: 'Restricción creada correctamente' });
      handleCloseDialog();
      fetchRestrictions();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Error al crear restricción' 
      });
    }
  };

  const handleDelete = async (restrictionId) => {
    if (!window.confirm('¿Eliminar esta restricción?')) return;
    
    try {
      await axios.delete(`${API_BASE}/restrictions/${restrictionId}`);
      setMessage({ type: 'success', text: 'Restricción eliminada' });
      fetchRestrictions();
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al eliminar restricción' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          🚫 Restricciones por Profesor
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenDialog}
        >
          Nueva Restricción
        </Button>
      </Box>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Profesor</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Día</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Horario</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Bloques</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Motivo</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {restrictions.map((restriction) => (
                  <TableRow key={restriction.id} hover>
                    <TableCell>{restriction.professor_name}</TableCell>
                    <TableCell>
                      <Chip label={restriction.day} size="small" color="primary" />
                    </TableCell>
                    <TableCell>
                      {restriction.start_time} - {restriction.end_time}
                    </TableCell>
                    <TableCell>{restriction.duration_blocks} bloques</TableCell>
                    <TableCell>{restriction.reason || '-'}</TableCell>
                    <TableCell align="center">
                      <IconButton 
                        size="small" 
                        color="error" 
                        onClick={() => handleDelete(restriction.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {restrictions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 5, color: '#999' }}>
                      No hay restricciones registradas
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BlockIcon color="error" />
            Nueva Restricción Horaria
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Profesor</InputLabel>
              <Select
                value={formData.professor_id}
                onChange={(e) => setFormData({...formData, professor_id: e.target.value})}
                label="Profesor"
              >
                {professors.map((prof) => (
                  <MenuItem key={prof.id} value={prof.id}>
                    {prof.nombre_completo}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Día</InputLabel>
              <Select
                value={formData.day}
                onChange={(e) => setFormData({...formData, day: e.target.value})}
                label="Día"
              >
                {DAYS.map((day) => (
                  <MenuItem key={day} value={day}>{day}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Hora Inicio</InputLabel>
              <Select
                value={formData.start_time}
                onChange={(e) => setFormData({...formData, start_time: e.target.value})}
                label="Hora Inicio"
              >
                {TIME_SLOTS.map((time) => (
                  <MenuItem key={time} value={time}>{time}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Hora Fin</InputLabel>
              <Select
                value={formData.end_time}
                onChange={(e) => setFormData({...formData, end_time: e.target.value})}
                label="Hora Fin"
              >
                {TIME_SLOTS.map((time) => (
                  <MenuItem key={time} value={time}>{time}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Motivo (opcional)"
              value={formData.reason}
              onChange={(e) => setFormData({...formData, reason: e.target.value})}
              fullWidth
              multiline
              rows={2}
              placeholder="Ej: Reunión administrativa, Clase en otra sede..."
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button 
            variant="contained" 
            onClick={handleSave}
            disabled={!formData.professor_id}
            startIcon={<AddIcon />}
          >
            Crear Restricción
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
