import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, Alert, CircularProgress,
  Chip, Card, CardContent, CardHeader, Avatar,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Tooltip, Grid, Switch, FormControlLabel,
  Snackbar, Badge, Fab
} from '@mui/material';
import {
  Save as SaveIcon,
  Person as PersonIcon,
  Schedule as ScheduleIcon,
  Block as BlockIcon,
  Clear as ClearIcon,
  Undo as UndoIcon,
  Redo as RedoIcon,
  SelectAll as SelectAllIcon,
  ContentCopy as CopyIcon,
  ContentPaste as PasteIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = 'http://localhost:8001/api';

// Configuración de horarios
const TIME_SLOTS = [
  '07:00', '07:50', '08:40', '09:40', '10:30', '11:20',
  '12:10', '13:00', '14:00', '14:50', '15:40', '16:30',
  '17:20', '18:20', '19:10', '20:00', '20:50', '21:40', '22:30'
];

const DAYS = [
  { key: 'lunes', label: 'LUNES', color: '#e3f2fd' },
  { key: 'martes', label: 'MARTES', color: '#f3e5f5' },
  { key: 'miercoles', label: 'MIÉRCOLES', color: '#e8f5e8' },
  { key: 'jueves', label: 'JUEVES', color: '#fff3e0' },
  { key: 'viernes', label: 'VIERNES', color: '#fce4ec' },
  { key: 'sabado', label: 'SÁBADO', color: '#f1f8e9' }
];

// Estados de celda
const CELL_STATES = {
  AVAILABLE: 'available',
  RESTRICTED: 'restricted',
  PARTIALLY_RESTRICTED: 'partial',
  UNAVAILABLE: 'unavailable'
};

// Component principal
export default function RestrictionsExcel() {
  const [professors, setProfessors] = useState([]);
  const [restrictions, setRestrictions] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [selectedCells, setSelectedCells] = useState(new Set());
  const [dragMode, setDragMode] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const [clipboard, setClipboard] = useState(null);
  const [saveDialog, setSaveDialog] = useState(false);

  useEffect(() => {
    fetchProfessors();
    fetchRestrictions();
  }, []);

  const fetchProfessors = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/professors`);
      setProfessors(response.data.professors || []);
    } catch (error) {
      showMessage('Error al cargar profesores', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchRestrictions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/assignments/restrictions`);
      const restrictionsData = {};
      
      // Organizar restricciones por profesor
      response.data.forEach(restriction => {
        if (!restrictionsData[restriction.professor_id]) {
          restrictionsData[restriction.professor_id] = {};
        }
        
        const cellKey = `${restriction.day.toLowerCase()}_${restriction.start_time}`;
        restrictionsData[restriction.professor_id][cellKey] = {
          id: restriction.id,
          start_time: restriction.start_time,
          end_time: restriction.end_time,
          reason: restriction.reason,
          state: CELL_STATES.RESTRICTED
        };
      });
      
      setRestrictions(restrictionsData);
    } catch (error) {
      showMessage('Error al cargar restricciones', 'error');
    }
  };

  const showMessage = (text, type = 'info') => {
    setMessage({ text, type });
  };

  const getCellKey = (professorId, day, timeSlot) => {
    return `${professorId}_${day}_${timeSlot}`;
  };

  const getCellState = (professorId, day, timeSlot) => {
    const cellKey = `${day}_${timeSlot}`;
    return restrictions[professorId]?.[cellKey]?.state || CELL_STATES.AVAILABLE;
  };

  const setCellState = (professorId, day, timeSlot, newState, reason = '') => {
    const cellKey = `${day}_${timeSlot}`;
    
    setRestrictions(prev => {
      const newRestrictions = { ...prev };
      
      if (!newRestrictions[professorId]) {
        newRestrictions[professorId] = {};
      }
      
      if (newState === CELL_STATES.AVAILABLE) {
        delete newRestrictions[professorId][cellKey];
      } else {
        newRestrictions[professorId][cellKey] = {
          start_time: timeSlot,
          end_time: getNextTimeSlot(timeSlot),
          reason: reason,
          state: newState
        };
      }
      
      return newRestrictions;
    });
    
    setHasChanges(true);
  };

  const getNextTimeSlot = (currentSlot) => {
    const currentIndex = TIME_SLOTS.indexOf(currentSlot);
    return currentIndex < TIME_SLOTS.length - 1 ? TIME_SLOTS[currentIndex + 1] : currentSlot;
  };

  const getCellStyle = (state, isSelected) => {
    const baseStyle = {
      minHeight: '40px',
      border: '1px solid #e0e0e0',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      position: 'relative',
      userSelect: 'none'
    };

    if (isSelected) {
      baseStyle.border = '2px solid #1976d2';
      baseStyle.boxShadow = '0 0 0 1px #1976d2';
    }

    switch (state) {
      case CELL_STATES.AVAILABLE:
        return { ...baseStyle, backgroundColor: '#f8f9fa', '&:hover': { backgroundColor: '#e9ecef' } };
      case CELL_STATES.RESTRICTED:
        return { ...baseStyle, backgroundColor: '#ffebee', '&:hover': { backgroundColor: '#ffcdd2' } };
      case CELL_STATES.PARTIALLY_RESTRICTED:
        return { ...baseStyle, backgroundColor: '#fff3e0', '&:hover': { backgroundColor: '#ffe0b2' } };
      case CELL_STATES.UNAVAILABLE:
        return { ...baseStyle, backgroundColor: '#fafafa', '&:hover': { backgroundColor: '#f5f5f5' } };
      default:
        return baseStyle;
    }
  };

  const handleCellMouseDown = (professorId, day, timeSlot, event) => {
    event.preventDefault();
    setIsDragging(true);
    setDragStart({ professorId, day, timeSlot });
    
    const currentState = getCellState(professorId, day, timeSlot);
    const newState = currentState === CELL_STATES.RESTRICTED ? CELL_STATES.AVAILABLE : CELL_STATES.RESTRICTED;
    setDragMode(newState);
    
    setCellState(professorId, day, timeSlot, newState);
    
    const cellKey = getCellKey(professorId, day, timeSlot);
    setSelectedCells(new Set([cellKey]));
  };

  const handleCellMouseEnter = (professorId, day, timeSlot) => {
    if (isDragging && dragMode !== null) {
      setCellState(professorId, day, timeSlot, dragMode);
      
      const cellKey = getCellKey(professorId, day, timeSlot);
      setSelectedCells(prev => new Set([...prev, cellKey]));
    }
  };

  const handleCellMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
    setDragMode(null);
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      if (isDragging) {
        handleCellMouseUp();
      }
    };

    document.addEventListener('mouseup', handleGlobalMouseUp);
    return () => document.removeEventListener('mouseup', handleGlobalMouseUp);
  }, [isDragging]);

  const saveAllChanges = async () => {
    if (!hasChanges) return;
    
    setLoading(true);
    try {
      // Preparar datos para envío
      const restrictionsToSave = [];
      
      Object.entries(restrictions).forEach(([professorId, professorRestrictions]) => {
        Object.entries(professorRestrictions).forEach(([cellKey, restriction]) => {
          const [day, timeSlot] = cellKey.split('_');
          
          restrictionsToSave.push({
            professor_id: parseInt(professorId),
            day: day.charAt(0).toUpperCase() + day.slice(1),
            start_time: restriction.start_time,
            end_time: restriction.end_time,
            reason: restriction.reason || 'Restricción manual'
          });
        });
      });

      // Primero eliminar todas las restricciones existentes
      await axios.delete(`${API_BASE}/assignments/restrictions/all`);
      
      // Luego crear las nuevas
      for (const restriction of restrictionsToSave) {
        await axios.post(`${API_BASE}/assignments/restrictions`, restriction);
      }
      
      setHasChanges(false);
      setSaveDialog(false);
      showMessage('Restricciones guardadas exitosamente', 'success');
      
      // Recargar datos
      await fetchRestrictions();
      
    } catch (error) {
      showMessage('Error al guardar restricciones', 'error');
    } finally {
      setLoading(false);
    }
  };

  const clearAllRestrictions = () => {
    setRestrictions({});
    setHasChanges(true);
    showMessage('Todas las restricciones han sido eliminadas', 'info');
  };

  const selectAllForProfessor = (professorId) => {
    const newSelected = new Set();
    DAYS.forEach(day => {
      TIME_SLOTS.forEach(timeSlot => {
        newSelected.add(getCellKey(professorId, day.key, timeSlot));
      });
    });
    setSelectedCells(newSelected);
  };

  const applyRestrictionToSelected = (state) => {
    selectedCells.forEach(cellKey => {
      const [professorId, day, timeSlot] = cellKey.split('_');
      setCellState(parseInt(professorId), day, timeSlot, state);
    });
    setSelectedCells(new Set());
  };

  if (loading && professors.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScheduleIcon />
          Restricciones de Profesores - Vista Excel
        </Typography>
        
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => { fetchRestrictions(); fetchProfessors(); }}
          >
            Actualizar
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<ClearIcon />}
            onClick={clearAllRestrictions}
            color="warning"
          >
            Limpiar Todo
          </Button>
          
          {hasChanges && (
            <Badge badgeContent="!" color="error">
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => setSaveDialog(true)}
                color="primary"
              >
                Guardar Cambios
              </Button>
            </Badge>
          )}
        </Box>
      </Box>

      {/* Leyenda */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Leyenda:</Typography>
        <Box display="flex" gap={2} flexWrap="wrap">
          <Chip 
            label="Disponible" 
            sx={{ bgcolor: '#f8f9fa' }}
            onClick={() => applyRestrictionToSelected(CELL_STATES.AVAILABLE)}
          />
          <Chip 
            label="Restringido" 
            sx={{ bgcolor: '#ffebee' }}
            onClick={() => applyRestrictionToSelected(CELL_STATES.RESTRICTED)}
          />
          <Typography variant="body2" color="textSecondary">
            • Clic y arrastra para seleccionar • Doble clic para seleccionar día completo
          </Typography>
        </Box>
      </Paper>

      {/* Grid principal */}
      {professors.map((professor) => (
        <Card key={professor.id} sx={{ mb: 3 }}>
          <CardHeader
            avatar={
              <Avatar sx={{ bgcolor: 'primary.main' }}>
                <PersonIcon />
              </Avatar>
            }
            title={professor.nombre_completo}
            subheader={`Código: ${professor.codigo}`}
            action={
              <Box>
                <Button
                  size="small"
                  onClick={() => selectAllForProfessor(professor.id)}
                  startIcon={<SelectAllIcon />}
                >
                  Seleccionar Todo
                </Button>
              </Box>
            }
          />
          
          <CardContent>
            <Box sx={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ 
                      padding: '8px', 
                      backgroundColor: '#f5f5f5', 
                      border: '1px solid #ddd',
                      minWidth: '80px',
                      fontSize: '12px'
                    }}>
                      HORA
                    </th>
                    {DAYS.map(day => (
                      <th 
                        key={day.key}
                        style={{ 
                          padding: '8px', 
                          backgroundColor: day.color, 
                          border: '1px solid #ddd',
                          minWidth: '100px',
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }}
                      >
                        {day.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {TIME_SLOTS.map(timeSlot => (
                    <tr key={timeSlot}>
                      <td style={{ 
                        padding: '4px 8px', 
                        backgroundColor: '#f9f9f9', 
                        border: '1px solid #ddd',
                        fontSize: '11px',
                        fontWeight: 'bold',
                        textAlign: 'center'
                      }}>
                        {timeSlot}
                      </td>
                      {DAYS.map(day => {
                        const cellKey = getCellKey(professor.id, day.key, timeSlot);
                        const cellState = getCellState(professor.id, day.key, timeSlot);
                        const isSelected = selectedCells.has(cellKey);
                        
                        return (
                          <td
                            key={`${day.key}_${timeSlot}`}
                            style={getCellStyle(cellState, isSelected)}
                            onMouseDown={(e) => handleCellMouseDown(professor.id, day.key, timeSlot, e)}
                            onMouseEnter={() => handleCellMouseEnter(professor.id, day.key, timeSlot)}
                            onDoubleClick={() => {
                              // Seleccionar todo el día
                              const daySelected = new Set();
                              TIME_SLOTS.forEach(slot => {
                                daySelected.add(getCellKey(professor.id, day.key, slot));
                              });
                              setSelectedCells(daySelected);
                            }}
                          >
                            <Box 
                              sx={{ 
                                height: '30px', 
                                display: 'flex', 
                                alignItems: 'center', 
                                justifyContent: 'center',
                                fontSize: '10px'
                              }}
                            >
                              {cellState === CELL_STATES.RESTRICTED && (
                                <BlockIcon sx={{ fontSize: 16, color: 'error.main' }} />
                              )}
                            </Box>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Box>
          </CardContent>
        </Card>
      ))}

      {/* Dialog de confirmación de guardado */}
      <Dialog open={saveDialog} onClose={() => setSaveDialog(false)}>
        <DialogTitle>Confirmar Guardado</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Estás seguro de que quieres guardar todos los cambios? 
            Esto reemplazará todas las restricciones existentes.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialog(false)}>Cancelar</Button>
          <Button 
            variant="contained" 
            onClick={saveAllChanges}
            disabled={loading}
          >
            {loading ? <CircularProgress size={20} /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar para mensajes */}
      <Snackbar
        open={!!message}
        autoHideDuration={4000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={() => setMessage(null)} 
          severity={message?.type || 'info'}
          sx={{ width: '100%' }}
        >
          {message?.text}
        </Alert>
      </Snackbar>

      {/* FAB para acciones rápidas */}
      {selectedCells.size > 0 && (
        <Fab
          color="primary"
          sx={{ position: 'fixed', bottom: 16, right: 16 }}
          onClick={() => applyRestrictionToSelected(CELL_STATES.RESTRICTED)}
        >
          <BlockIcon />
        </Fab>
      )}
    </Box>
  );
}