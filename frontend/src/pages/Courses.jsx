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
  School as CourseIcon
} from '@mui/icons-material';
import { projectionsAPI } from '../api/projectionsAPI';

export default function Courses() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);
  const [formData, setFormData] = useState({
    codigo: '',
    nombre: '',
    ciclo: 1,
    creditos: 3,
    alumnos_teoria: 0,
    alumnos_practica: 0,
    alumnos_laboratorio: 0,
    requiere_laboratorio: false,
    requiere_practica: false
  });

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const data = await projectionsAPI.getCourses();
      setCourses(data.courses || []);
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al cargar cursos' });
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (course = null) => {
    if (course) {
      setEditingCourse(course);
      setFormData({
        codigo: course.codigo,
        nombre: course.nombre,
        ciclo: course.ciclo || 1,
        modalidad: (course.modalidad || 'PRESENCIAL').toUpperCase(),
        creditos: course.creditos || 3,
        alumnos_teoria: course.alumnos_teoria || 0,
        alumnos_practica: course.alumnos_practica || 0,
        alumnos_laboratorio: course.alumnos_laboratorio || 0,
        grupos_teoria: course.grupos_teoria || 0,
        grupos_practica: course.grupos_practica || 0,
        grupos_laboratorio: course.grupos_laboratorio || 0,
        requiere_laboratorio: course.requiere_laboratorio || false,
        requiere_practica: course.requiere_practica || false
      });
    } else {
      setEditingCourse(null);
      setFormData({
        codigo: '',
        nombre: '',
        ciclo: 1,
        modalidad: 'PRESENCIAL',
        creditos: 3,
        alumnos_teoria: 0,
        alumnos_practica: 0,
        alumnos_laboratorio: 0,
        grupos_teoria: 0,
        grupos_practica: 0,
        grupos_laboratorio: 0,
        requiere_laboratorio: false,
        requiere_practica: false
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingCourse(null);
  };

  const sanitizeNumber = (value, min = 0) => {
    const parsed = parseInt(value, 10);
    if (Number.isNaN(parsed)) return min;
    return parsed < min ? min : parsed;
  };

  const handleChange = (field) => (event) => {
    let value = event.target.value;

    if (['codigo'].includes(field)) {
      value = value.toUpperCase().replace(/\s+/g, '');
    }

    if ([
      'ciclo',
      'creditos',
      'alumnos_teoria',
      'alumnos_practica',
      'alumnos_laboratorio',
      'grupos_teoria',
      'grupos_practica',
      'grupos_laboratorio'
    ].includes(field)) {
      const minimums = {
        ciclo: 1,
        creditos: 1
      };
      value = sanitizeNumber(value, minimums[field] ?? 0);
    }

    setFormData((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleModalidadChange = (event) => {
    const value = event.target.value;
    setFormData((prev) => ({ ...prev, modalidad: value }));
  };

  const handleBooleanSelect = (field) => (event) => {
    setFormData((prev) => ({
      ...prev,
      [field]: event.target.value === 'Sí'
    }));
  };

  const handleSave = async () => {
    try {
      if (editingCourse) {
        await projectionsAPI.updateCourse(editingCourse.id, formData);
        setMessage({ type: 'success', text: 'Curso actualizado' });
      } else {
        await projectionsAPI.createCourse(formData);
        setMessage({ type: 'success', text: 'Curso creado' });
      }
      handleCloseDialog();
      fetchCourses();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Error al guardar curso' 
      });
    }
  };

  const handleDelete = async (courseId) => {
    if (!window.confirm('¿Eliminar este curso?')) return;
    
    try {
      await projectionsAPI.deleteCourse(courseId);
      setMessage({ type: 'success', text: 'Curso eliminado' });
      fetchCourses();
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al eliminar curso' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          📚 Gestión de Cursos
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Nuevo Curso
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
          <TableContainer sx={{ maxHeight: 600 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Código</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Nombre</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Ciclo</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Créditos</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Grupos T</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Grupos P</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Grupos L</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {courses.map((course) => (
                  <TableRow key={course.id} hover>
                    <TableCell>{course.codigo}</TableCell>
                    <TableCell>{course.nombre}</TableCell>
                    <TableCell align="center">
                      <Chip label={`Ciclo ${course.ciclo}`} size="small" color="primary" />
                    </TableCell>
                    <TableCell align="center">{course.creditos}</TableCell>
                    <TableCell align="center">
                      <Chip 
                        label={course.grupos_teoria || 0} 
                        size="small" 
                        color={course.grupos_teoria > 0 ? "success" : "default"}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip 
                        label={course.grupos_practica || 0} 
                        size="small" 
                        color={course.grupos_practica > 0 ? "info" : "default"}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip 
                        label={course.grupos_laboratorio || 0} 
                        size="small" 
                        color={course.grupos_laboratorio > 0 ? "warning" : "default"}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <IconButton size="small" onClick={() => handleOpenDialog(course)}>
                        <EditIcon />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDelete(course.id)}>
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

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CourseIcon color="primary" />
            {editingCourse ? 'Editar Curso' : 'Nuevo Curso'}
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, pt: 2 }}>
            <TextField
              label="Código"
              value={formData.codigo}
              onChange={handleChange('codigo')}
              disabled={!!editingCourse}
            />
            <TextField
              label="Ciclo"
              type="number"
              value={formData.ciclo}
              onChange={handleChange('ciclo')}
            />
            <TextField
              label="Nombre del Curso"
              value={formData.nombre}
              onChange={handleChange('nombre')}
              fullWidth
              sx={{ gridColumn: 'span 2' }}
            />
            <TextField
              label="Modalidad"
              value={formData.modalidad}
              onChange={handleModalidadChange}
              select
            >
              <MenuItem value="PRESENCIAL">Presencial</MenuItem>
              <MenuItem value="NO_PRESENCIAL">No Presencial</MenuItem>
            </TextField>
            <TextField
              label="Créditos"
              type="number"
              value={formData.creditos}
              onChange={handleChange('creditos')}
            />
            
            <Typography variant="subtitle2" sx={{ gridColumn: 'span 2', mt: 1, color: '#666' }}>
              📊 Número de Alumnos Proyectados
            </Typography>
            <TextField
              label="Alumnos Teoría"
              type="number"
              value={formData.alumnos_teoria}
              onChange={handleChange('alumnos_teoria')}
            />
            <TextField
              label="Alumnos Práctica"
              type="number"
              value={formData.alumnos_practica}
              onChange={handleChange('alumnos_practica')}
            />
            <TextField
              label="Alumnos Laboratorio"
              type="number"
              value={formData.alumnos_laboratorio}
              onChange={handleChange('alumnos_laboratorio')}
              sx={{ gridColumn: 'span 2' }}
            />
            
            <Typography variant="subtitle2" sx={{ gridColumn: 'span 2', mt: 1, color: '#ff6f00', fontWeight: 'bold' }}>
              ⚠️ Número de Grupos (CRÍTICO para generación de horarios)
            </Typography>
            <TextField
              label="Grupos Teoría"
              type="number"
              value={formData.grupos_teoria}
              onChange={handleChange('grupos_teoria')}
              sx={{ bgcolor: '#fff3e0' }}
            />
            <TextField
              label="Grupos Práctica"
              type="number"
              value={formData.grupos_practica}
              onChange={handleChange('grupos_practica')}
              sx={{ bgcolor: '#fff3e0' }}
            />
            <TextField
              label="Grupos Laboratorio"
              type="number"
              value={formData.grupos_laboratorio}
              onChange={handleChange('grupos_laboratorio')}
              sx={{ gridColumn: 'span 2', bgcolor: '#fff3e0' }}
            />
            
            <TextField
              label="Requiere Práctica"
              value={formData.requiere_practica ? 'Sí' : 'No'}
              onChange={handleBooleanSelect('requiere_practica')}
              select
            >
              <MenuItem value="Sí">Sí</MenuItem>
              <MenuItem value="No">No</MenuItem>
            </TextField>
            <TextField
              label="Requiere Laboratorio"
              value={formData.requiere_laboratorio ? 'Sí' : 'No'}
              onChange={handleBooleanSelect('requiere_laboratorio')}
              select
            >
              <MenuItem value="Sí">Sí</MenuItem>
              <MenuItem value="No">No</MenuItem>
            </TextField>
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
            disabled={!formData.codigo || !formData.nombre}
          >
            {editingCourse ? 'Actualizar' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
