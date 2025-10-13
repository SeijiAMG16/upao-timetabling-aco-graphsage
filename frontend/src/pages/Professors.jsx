import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Paper, Typography, Button, TextField, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, IconButton,
  Snackbar, Alert, Stack
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = 'http://localhost:8001/api/professors';

export default function Professors() {
  const [professors, setProfessors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingProf, setEditingProf] = useState(null);
  const [formData, setFormData] = useState({
    codigo: '',
    nombre_completo: ''
  });
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchProfessors();
  }, []);

  const fetchProfessors = async () => {
    setLoading(true);
    try {
      const response = await axios.get(API_BASE);
      setProfessors(response.data.professors || []);
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al cargar profesores' });
    } finally {
      setLoading(false);
    }
  };

  const filteredProfessors = useMemo(() => {
    if (!searchTerm.trim()) return professors;
    const value = searchTerm.toLowerCase();
    return professors.filter(
      (prof) =>
        prof.codigo?.toLowerCase().includes(value) ||
        prof.nombre_completo?.toLowerCase().includes(value)
    );
  }, [professors, searchTerm]);

  const handleFieldChange = (field) => (event) => {
    let { value } = event.target;

    if (field === 'codigo') {
      value = value.toUpperCase().replace(/\s+/g, '');
    } else if (field === 'nombre_completo') {
      value = value.replace(/[ ]{2,}/g, ' ');
    }

    setFormData((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCloseMessage = () => setMessage(null);

  const handleOpenDialog = (professor = null) => {
    if (professor) {
      setEditingProf(professor);
      setFormData({
        codigo: professor.codigo,
        nombre_completo: professor.nombre_completo || ''
      });
    } else {
      setEditingProf(null);
      setFormData({
        codigo: '',
        nombre_completo: ''
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingProf(null);
    setFormData({
      codigo: '',
      nombre_completo: ''
    });
  };

  const handleSave = async () => {
    try {
      if (editingProf) {
        await axios.put(`${API_BASE}/${editingProf.id}`, formData);
        setMessage({ type: 'success', text: 'Profesor actualizado' });
      } else {
        await axios.post(API_BASE, formData);
        setMessage({ type: 'success', text: 'Profesor creado' });
      }
      handleCloseDialog();
      fetchProfessors();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Error al guardar profesor' 
      });
    }
  };

  const handleDelete = async (profId) => {
    if (!window.confirm('¿Eliminar este profesor?')) return;
    
    try {
      await axios.delete(`${API_BASE}/${profId}`);
      setMessage({ type: 'success', text: 'Profesor eliminado' });
      fetchProfessors();
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al eliminar profesor' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          👨‍🏫 Profesores Disponibles
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Nuevo Profesor
        </Button>
      </Box>

      <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
          <TextField
            label="Buscar por código o nombre"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Ej. P001 o Juan"
            fullWidth
          />
          <Typography variant="body2" color="text.secondary">
            {filteredProfessors.length} de {professors.length} profesores
          </Typography>
        </Stack>

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
                  <TableCell sx={{ fontWeight: 700 }}>Nombre Completo</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredProfessors.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} align="center" sx={{ py: 4 }}>
                      No se encontraron profesores que coincidan con la búsqueda.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredProfessors.map((prof) => (
                    <TableRow key={prof.id} hover>
                      <TableCell sx={{ fontFamily: 'monospace', letterSpacing: 0.5 }}>{prof.codigo}</TableCell>
                      <TableCell>{prof.nombre_completo}</TableCell>
                      <TableCell align="center">
                        <IconButton size="small" onClick={() => handleOpenDialog(prof)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDelete(prof.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingProf ? 'Editar Profesor' : 'Nuevo Profesor'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField
              label="Código"
              value={formData.codigo}
              onChange={handleFieldChange('codigo')}
              fullWidth
              disabled={!!editingProf}
              helperText="Usa el código institucional en mayúsculas, sin espacios."
              inputProps={{ style: { textTransform: 'uppercase' } }}
            />
            <TextField
              label="Nombre completo"
              value={formData.nombre_completo}
              onChange={handleFieldChange('nombre_completo')}
              fullWidth
              helperText="Ejemplo: Juan Pérez Díaz"
            />
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
            disabled={!formData.codigo || !formData.nombre_completo}
          >
            {editingProf ? 'Actualizar' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={4000}
        onClose={handleCloseMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {message && (
          <Alert
            onClose={handleCloseMessage}
            severity={message.type}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {message.text}
          </Alert>
        )}
      </Snackbar>
    </Box>
  );
}
