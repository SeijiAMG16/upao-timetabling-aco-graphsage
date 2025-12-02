import React, { useState } from 'react';
import {
  Box, Button, Paper, Typography, Alert, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, IconButton
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import CheckIcon from '@mui/icons-material/Check';
import CancelIcon from '@mui/icons-material/Cancel';
import PeopleIcon from '@mui/icons-material/People';
import BlockIcon from '@mui/icons-material/Block';
import axios from 'axios';

const API_BASE = `${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api`;

export default function ProfessorsUpload() {
  const [file, setFile] = useState(null);
  const [professors, setProfessors] = useState([]);
  const [restrictions, setRestrictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Selecciona un archivo primero' });
      return;
    }

    setLoading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/professors-upload/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setProfessors(response.data.professors);
      setRestrictions(response.data.restrictions);
      setMessage({
        type: 'info',
        text: `${response.data.total_professors} profesores extraídos con ${response.data.total_restrictions} restricciones horarias. Revisa y confirma.`
      });
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Error al procesar Excel'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const response = await axios.post(`${API_BASE}/professors-upload/confirm`, {
        professors: professors,
        restrictions: restrictions
      });

      setMessage({ type: 'success', text: response.data.message });
      // Limpiar después de guardar
      setTimeout(() => {
        setProfessors([]);
        setRestrictions([]);
        setFile(null);
      }, 2000);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Error al guardar profesores'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setProfessors([]);
    setRestrictions([]);
    setFile(null);
    setMessage(null);
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
        <PeopleIcon color="primary" fontSize="large" />
        Upload de Profesores y Restricciones
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          📂 Cargar Excel de Horarios de Docentes
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Selecciona el archivo <strong>Horario_Docentes(2025-20).xlsx</strong> para extraer
          profesores y sus restricciones horarias automáticamente.
        </Typography>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadIcon />}
          >
            {file ? file.name : 'Seleccionar Excel'}
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

      {professors.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Revisar y Confirmar ({professors.length} profesores, {restrictions.length} restricciones)
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                color="error"
                startIcon={<CancelIcon />}
                onClick={handleCancel}
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

          <TableContainer sx={{ maxHeight: 500 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Código</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Nombre Completo</TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <BlockIcon fontSize="small" />
                      Restricciones
                    </Box>
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }} align="center">Estado</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {professors.map((prof) => (
                  <TableRow key={prof.codigo} hover>
                    <TableCell>{prof.codigo}</TableCell>
                    <TableCell>{prof.nombre_completo}</TableCell>
                    <TableCell align="center">
                      <Chip 
                        label={prof.restrictions_count} 
                        size="small" 
                        color="warning"
                        icon={<BlockIcon />}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Chip 
                        label={prof.exists ? 'Actualizar' : 'Nuevo'} 
                        color={prof.exists ? 'info' : 'success'} 
                        size="small" 
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
              ℹ️ Información importante:
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Las restricciones horarias se extraen automáticamente de los bloques ocupados en el Excel
              <br />
              • Los profesores existentes en la BD se actualizarán preservando sus datos
              <br />
              • Tu única tarea manual será asignar profesores a cursos desde la interfaz de asignaciones
            </Typography>
          </Box>
        </Paper>
      )}
    </Box>
  );
}
