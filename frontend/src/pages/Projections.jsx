import React, { useState } from 'react';
import {
  Box, Paper, Typography, Button, Alert, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, IconButton, Chip
} from '@mui/material';
import {
  Upload as UploadIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Delete as DeleteIcon,
  Edit as EditIcon
} from '@mui/icons-material';
import { projectionsAPI } from '../api/projectionsAPI';

export default function Projections() {
  const [file, setFile] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});

  const handleFileSelect = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Selecciona un archivo Excel primero' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const result = await projectionsAPI.uploadExcel(file);
      // Agregar ID único a cada curso para manejar duplicados
      const coursesWithId = (result.courses || []).map((course, idx) => ({
        ...course,
        _uniqueId: `${course.codigo}-${idx}`
      }));
      setCourses(coursesWithId);
      setMessage({ 
        type: 'success', 
        text: result.message || `${coursesWithId.length} cursos extraídos. Revisa y confirma.` 
      });
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Error al procesar el archivo' 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (courses.length === 0) {
      setMessage({ type: 'error', text: 'No hay datos para confirmar' });
      return;
    }

    setLoading(true);
    try {
      // Limpiar _uniqueId antes de enviar al backend
      const cleanedCourses = courses.map(({ _uniqueId, ...course }) => course);
      const result = await projectionsAPI.confirmProjections(cleanedCourses);
      setMessage({ type: 'success', text: result.message });
      setCourses([]);
      setFile(null);
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Error al guardar proyecciones' 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setCourses([]);
    setFile(null);
    setMessage(null);
  };

  const handleEdit = (course) => {
    setEditingId(course._uniqueId);
    setEditValues({ ...course });
  };

  const handleSaveEdit = () => {
    setCourses(courses.map(c => 
      c._uniqueId === editingId ? { ...editValues } : c
    ));
    setEditingId(null);
    setEditValues({});
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleDelete = (uniqueId) => {
    setCourses(courses.filter(c => c._uniqueId !== uniqueId));
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 700 }}>
        📊 Proyecciones de Cursos
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Cargar Excel de Proyecciones</Typography>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadIcon />}
            disabled={loading}
          >
            {file ? file.name : 'Seleccionar Libro1.xlsx'}
            <input
              type="file"
              hidden
              accept=".xlsx"
              onChange={handleFileSelect}
            />
          </Button>

          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={!file || loading}
            startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {loading ? 'Procesando...' : 'Procesar Excel'}
          </Button>
        </Box>
      </Paper>

      {courses.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Revisar y Confirmar ({courses.length} cursos)
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                color="error"
                startIcon={<CancelIcon />}
                onClick={handleCancel}
                disabled={loading}
              >
                Cancelar
              </Button>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckIcon />}
                onClick={handleConfirm}
                disabled={loading}
              >
                {loading ? 'Guardando...' : 'Confirmar y Guardar'}
              </Button>
            </Box>
          </Box>

          <TableContainer sx={{ maxHeight: 600 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Código</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Nombre</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Ciclo</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Modalidad</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Alumnos T</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Alumnos P</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Alumnos L</TableCell>
                  <TableCell sx={{ fontWeight: 700, bgcolor: '#fff3e0' }} align="center">Grupos T</TableCell>
                  <TableCell sx={{ fontWeight: 700, bgcolor: '#fff3e0' }} align="center">Grupos P</TableCell>
                  <TableCell sx={{ fontWeight: 700, bgcolor: '#fff3e0' }} align="center">Grupos L</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Créditos</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Estado</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {courses.map((course) => (
                  <TableRow key={course._uniqueId} hover>
                    {editingId === course._uniqueId ? (
                      <>
                        <TableCell>{course.codigo}</TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            fullWidth
                            value={editValues.nombre}
                            onChange={(e) => setEditValues({...editValues, nombre: e.target.value})}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.ciclo}
                            onChange={(e) => setEditValues({...editValues, ciclo: parseInt(e.target.value)})}
                            sx={{ width: 60 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.alumnos_teoria}
                            onChange={(e) => setEditValues({...editValues, alumnos_teoria: parseInt(e.target.value)})}
                            sx={{ width: 80 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.alumnos_practica}
                            onChange={(e) => setEditValues({...editValues, alumnos_practica: parseInt(e.target.value)})}
                            sx={{ width: 80 }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.alumnos_laboratorio}
                            onChange={(e) => setEditValues({...editValues, alumnos_laboratorio: parseInt(e.target.value)})}
                            sx={{ width: 80 }}
                          />
                        </TableCell>
                        <TableCell align="center" sx={{ bgcolor: '#fff3e0' }}>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.grupos_teoria || 0}
                            onChange={(e) => setEditValues({...editValues, grupos_teoria: parseInt(e.target.value)})}
                            sx={{ width: 60, fontWeight: 'bold' }}
                          />
                        </TableCell>
                        <TableCell align="center" sx={{ bgcolor: '#fff3e0' }}>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.grupos_practica || 0}
                            onChange={(e) => setEditValues({...editValues, grupos_practica: parseInt(e.target.value)})}
                            sx={{ width: 60, fontWeight: 'bold' }}
                          />
                        </TableCell>
                        <TableCell align="center" sx={{ bgcolor: '#fff3e0' }}>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.grupos_laboratorio || 0}
                            onChange={(e) => setEditValues({...editValues, grupos_laboratorio: parseInt(e.target.value)})}
                            sx={{ width: 60, fontWeight: 'bold' }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={editValues.creditos}
                            onChange={(e) => setEditValues({...editValues, creditos: parseInt(e.target.value)})}
                            sx={{ width: 60 }}
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Chip label="Editando" color="warning" size="small" />
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small" color="success" onClick={handleSaveEdit}>
                            <CheckIcon />
                          </IconButton>
                          <IconButton size="small" color="error" onClick={handleCancelEdit}>
                            <CancelIcon />
                          </IconButton>
                        </TableCell>
                      </>
                    ) : (
                      <>
                        <TableCell>{course.codigo}</TableCell>
                        <TableCell>{course.nombre}</TableCell>
                        <TableCell align="center">{course.ciclo}</TableCell>
                        <TableCell align="center">
                          <Chip 
                            label={course.modalidad === 'PRESENCIAL' ? 'PRS' : 'NPR'}
                            color={course.modalidad === 'PRESENCIAL' ? 'success' : 'warning'}
                            size="small"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        </TableCell>
                        <TableCell align="center">{course.alumnos_teoria}</TableCell>
                        <TableCell align="center">{course.alumnos_practica}</TableCell>
                        <TableCell align="center">{course.alumnos_laboratorio}</TableCell>
                        <TableCell align="center" sx={{ bgcolor: '#fff3e0', fontWeight: 'bold' }}>{course.grupos_teoria || 0}</TableCell>
                        <TableCell align="center" sx={{ bgcolor: '#fff3e0', fontWeight: 'bold' }}>{course.grupos_practica || 0}</TableCell>
                        <TableCell align="center" sx={{ bgcolor: '#fff3e0', fontWeight: 'bold' }}>{course.grupos_laboratorio || 0}</TableCell>
                        <TableCell align="center">{course.creditos}</TableCell>
                        <TableCell align="center">
                          <Chip 
                            label={course.exists ? 'Actualizar' : 'Nuevo'} 
                            color={course.exists ? 'primary' : 'success'} 
                            size="small" 
                          />
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small" onClick={() => handleEdit(course)}>
                            <EditIcon />
                          </IconButton>
                          <IconButton size="small" color="error" onClick={() => handleDelete(course._uniqueId)}>
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
}
