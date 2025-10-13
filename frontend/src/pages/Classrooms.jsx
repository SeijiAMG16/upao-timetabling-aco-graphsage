import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Button, Alert, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  IconButton, Chip, MenuItem
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  MeetingRoom as ClassroomIcon
} from '@mui/icons-material';
import { classroomsAPI } from '../api/classroomsAPI';

export default function Classrooms() {
  const [classrooms, setClassrooms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingRoom, setEditingRoom] = useState(null);
  const [formData, setFormData] = useState({
    codigo: '',
    edificio: '',
    piso: 1,
    capacidad: 30,
    tipo: 'Aula',
    tiene_computadoras: false,
    numero_computadoras: 0
  });

  useEffect(() => {
    fetchClassrooms();
  }, []);

  const fetchClassrooms = async () => {
    setLoading(true);
    try {
      const data = await classroomsAPI.getClassrooms();
      setClassrooms(data.classrooms || []);
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al cargar aulas' });
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (classroom = null) => {
    if (classroom) {
      setEditingRoom(classroom);
      setFormData({
        codigo: classroom.codigo,
        edificio: classroom.edificio || '',
        piso: classroom.piso || 1,
        capacidad: classroom.capacidad || 30,
        tipo: classroom.tipo || 'Aula',
        tiene_computadoras: classroom.tiene_computadoras || false,
        numero_computadoras: classroom.numero_computadoras || 0
      });
    } else {
      setEditingRoom(null);
      setFormData({
        codigo: '',
        edificio: '',
        piso: 1,
        capacidad: 30,
        tipo: 'Aula',
        tiene_computadoras: false,
        numero_computadoras: 0
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingRoom(null);
  };

  const handleSave = async () => {
    try {
      if (editingRoom) {
        await classroomsAPI.updateClassroom(editingRoom.id, formData);
        setMessage({ type: 'success', text: 'Aula actualizada' });
      } else {
        await classroomsAPI.createClassroom(formData);
        setMessage({ type: 'success', text: 'Aula creada' });
      }
      handleCloseDialog();
      fetchClassrooms();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Error al guardar aula' 
      });
    }
  };

  const handleDelete = async (roomId) => {
    if (!window.confirm('¿Eliminar esta aula?')) return;
    
    try {
      await classroomsAPI.deleteClassroom(roomId);
      setMessage({ type: 'success', text: 'Aula eliminada' });
      fetchClassrooms();
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al eliminar aula' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          🏫 Aulas y Salones
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Nueva Aula
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
                  <TableCell sx={{ fontWeight: 700 }}>Código</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Edificio</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Piso</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Capacidad</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">PCs</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {classrooms.map((room) => (
                  <TableRow key={room.id} hover>
                    <TableCell>{room.codigo}</TableCell>
                    <TableCell>{room.edificio}</TableCell>
                    <TableCell align="center">{room.piso}</TableCell>
                    <TableCell align="center">{room.capacidad}</TableCell>
                    <TableCell>
                      <Chip label={room.tipo} size="small" color="primary" />
                    </TableCell>
                    <TableCell align="center">
                      {room.tiene_computadoras ? `✅ ${room.numero_computadoras}` : '❌'}
                    </TableCell>
                    <TableCell align="center">
                      <IconButton size="small" onClick={() => handleOpenDialog(room)}>
                        <EditIcon />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDelete(room.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ClassroomIcon color="primary" />
            {editingRoom ? 'Editar Aula' : 'Nueva Aula'}
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField
              label="Código"
              value={formData.codigo}
              onChange={(e) => setFormData({...formData, codigo: e.target.value})}
              fullWidth
              disabled={!!editingRoom}
            />
            <TextField
              label="Edificio"
              value={formData.edificio}
              onChange={(e) => setFormData({...formData, edificio: e.target.value})}
              fullWidth
            />
            <TextField
              label="Piso"
              type="number"
              value={formData.piso}
              onChange={(e) => setFormData({...formData, piso: parseInt(e.target.value)})}
              fullWidth
            />
            <TextField
              label="Capacidad"
              type="number"
              value={formData.capacidad}
              onChange={(e) => setFormData({...formData, capacidad: parseInt(e.target.value)})}
              fullWidth
            />
            <TextField
              label="Tipo"
              value={formData.tipo}
              onChange={(e) => setFormData({...formData, tipo: e.target.value})}
              fullWidth
              select
            >
              <MenuItem value="Aula">Aula</MenuItem>
              <MenuItem value="Laboratorio">Laboratorio</MenuItem>
              <MenuItem value="Auditorio">Auditorio</MenuItem>
            </TextField>
            <TextField
              label="¿Tiene computadoras?"
              value={formData.tiene_computadoras ? 'Sí' : 'No'}
              onChange={(e) => setFormData({...formData, tiene_computadoras: e.target.value === 'Sí'})}
              fullWidth
              select
            >
              <MenuItem value="Sí">Sí</MenuItem>
              <MenuItem value="No">No</MenuItem>
            </TextField>
            {formData.tiene_computadoras && (
              <TextField
                label="Número de Computadoras"
                type="number"
                value={formData.numero_computadoras}
                onChange={(e) => setFormData({...formData, numero_computadoras: parseInt(e.target.value)})}
                fullWidth
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button startIcon={<CancelIcon />} onClick={handleCloseDialog}>
            Cancelar
          </Button>
          <Button 
            startIcon={<SaveIcon />} 
            variant="contained" 
            onClick={handleSave}
            disabled={!formData.codigo || !formData.edificio}
          >
            {editingRoom ? 'Actualizar' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
