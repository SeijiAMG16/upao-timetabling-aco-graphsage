import React, { useState, useEffect, useMemo } from 'react';
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Paper,
  Snackbar,
  Typography
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Block as BlockIcon,
  Clear as ClearIcon,
  Person as PersonIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = `${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api`;

const DAYS = [
  { key: 'lunes', title: 'LUNES', color: '#e3f2fd' },
  { key: 'martes', title: 'MARTES', color: '#f3e5f5' },
  { key: 'miercoles', title: 'MIÉRCOLES', color: '#e8f5e9' },
  { key: 'jueves', title: 'JUEVES', color: '#fff3e0' },
  { key: 'viernes', title: 'VIERNES', color: '#fce4ec' },
  { key: 'sabado', title: 'SÁBADO', color: '#f1f8e9' }
];

const DAY_LABELS = {
  lunes: 'Lunes',
  martes: 'Martes',
  miercoles: 'Miercoles',
  jueves: 'Jueves',
  viernes: 'Viernes',
  sabado: 'Sabado'
};

const HORARIOS = [
  { inicio: '07:00am', termino: '07:50am' },
  { inicio: '07:55am', termino: '08:45am' },
  { inicio: '08:50am', termino: '09:40am' },
  { inicio: '09:45am', termino: '10:35am' },
  { inicio: '10:40am', termino: '11:30am' },
  { inicio: '11:35am', termino: '12:25pm' },
  { inicio: '12:30pm', termino: '01:20pm' },
  { inicio: '01:25pm', termino: '02:15pm' },
  { inicio: '02:20pm', termino: '03:10pm' },
  { inicio: '03:15pm', termino: '04:05pm' },
  { inicio: '04:10pm', termino: '05:00pm' },
  { inicio: '05:05pm', termino: '05:55pm' },
  { inicio: '06:00pm', termino: '06:50pm' },
  { inicio: '06:55pm', termino: '07:45pm' },
  { inicio: '07:50pm', termino: '08:40pm' },
  { inicio: '08:45pm', termino: '09:35pm' },
  { inicio: '09:40pm', termino: '10:30pm' }
];

const SLOT_INDEX_LOOKUP = HORARIOS.reduce((acc, slot, index) => {
  acc[slot.inicio] = index;
  return acc;
}, {});

const CELL_STATE = {
  AVAILABLE: 'available',
  RESTRICTED: 'restricted'
};

const normalizeDayKey = (rawDay) => {
  if (!rawDay) return '';
  return rawDay
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
};

const convertToBackendTime = (timeAmPm) => {
  const [time, period] = timeAmPm.split(/(?=[ap]m)/);
  const [hours, minutes] = time.split(':');
  let hour = parseInt(hours, 10);

  if (period === 'pm' && hour !== 12) {
    hour += 12;
  } else if (period === 'am' && hour === 12) {
    hour = 0;
  }

  return `${hour.toString().padStart(2, '0')}:${minutes}:00`;
};

const convertFromBackendTime = (time24h) => {
  if (!time24h) return '';

  const [rawHours, rawMinutes] = time24h.split(':');
  let hour = parseInt(rawHours, 10);
  const minutes = rawMinutes;
  const period = hour >= 12 ? 'pm' : 'am';

  if (hour === 0) {
    hour = 12;
  } else if (hour > 12) {
    hour -= 12;
  }

  return `${hour.toString().padStart(2, '0')}:${minutes}${period}`;
};

const ProfessorRestrictions = () => {
  const [professors, setProfessors] = useState([]);
  const [restrictionsCount, setRestrictionsCount] = useState({});
  const [selectedProfessor, setSelectedProfessor] = useState(null);
  const [cells, setCells] = useState({});
  const [loadingProfessors, setLoadingProfessors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [pendingSave, setPendingSave] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragMode, setDragMode] = useState(null); // 'add' | 'remove'

  useEffect(() => {
    loadProfessors();
    loadRestrictionsCount();
  }, []);

  useEffect(() => {
    if (selectedProfessor) {
      loadProfessorRestrictions(selectedProfessor.id);
    }
  }, [selectedProfessor]);

  const loadProfessors = async () => {
    setLoadingProfessors(true);
    try {
      console.log('[restrictions] fetching professors');
      const { data } = await axios.get(`${API_BASE}/professors`);
      console.log('[restrictions] professors response', data);
      setProfessors(data.professors || []);
    } catch (error) {
      console.error('[restrictions] failed fetching professors', error);
      setMessage({ type: 'error', text: 'Error al cargar profesores' });
    } finally {
      setLoadingProfessors(false);
    }
  };

  const loadRestrictionsCount = async () => {
    try {
      console.log('[restrictions] fetching restriction counts');
      const { data } = await axios.get(`${API_BASE}/assignments/restrictions`);
      const counts = {};
      (data || []).forEach((item) => {
        counts[item.professor_id] = (counts[item.professor_id] || 0) + 1;
      });
      console.log('[restrictions] counts', counts);
      setRestrictionsCount(counts);
    } catch (error) {
      console.error('[restrictions] failed fetching counts', error);
    }
  };

  const loadProfessorRestrictions = async (professorId) => {
    try {
      console.log(`[restrictions] fetching entries for ${professorId}`);
      const { data } = await axios.get(`${API_BASE}/assignments/restrictions/professor/${professorId}`);
      console.log('[restrictions] entries', data);
      const normalized = {};

      (data || []).forEach((entry) => {
        const dayKey = normalizeDayKey(entry.day);
        if (!DAY_LABELS[dayKey]) {
          console.warn('[restrictions] unknown day', entry);
          return;
        }

        const slotKey = convertFromBackendTime(entry.start_time);
        const duration = Math.max(entry.duration_blocks || 1, 1);
        const baseIndex = SLOT_INDEX_LOOKUP[slotKey];

        if (typeof baseIndex !== 'number') {
          console.warn('[restrictions] slot not found', entry);
          return;
        }

        for (let offset = 0; offset < duration; offset += 1) {
          const slot = HORARIOS[baseIndex + offset];
          if (!slot) {
            console.warn('[restrictions] duration overflow', entry);
            break;
          }
          normalized[`${dayKey}_${slot.inicio}`] = {
            start_time: slot.inicio,
            end_time: slot.termino,
            reason: entry.reason || 'Restricción'
          };
        }
      });

      setCells(normalized);
      setPendingSave(false);
    } catch (error) {
      console.error('[restrictions] failed fetching entries', error);
      setMessage({ type: 'error', text: 'Error al cargar restricciones del profesor' });
      setCells({});
    }
  };

  const tableStyle = useMemo(
    () => ({
      borderCollapse: 'collapse',
      width: '100%'
    }),
    []
  );

  const getCellState = (dayKey, timeKey) => {
    return cells[`${dayKey}_${timeKey}`] ? CELL_STATE.RESTRICTED : CELL_STATE.AVAILABLE;
  };

  const applyCellState = (dayKey, timeKey, restrict) => {
    let updated = false;

    setCells((prev) => {
      const cellKey = `${dayKey}_${timeKey}`;

      if (restrict) {
        if (prev[cellKey]) return prev;
        updated = true;
        const slot = HORARIOS.find((item) => item.inicio === timeKey);
        return {
          ...prev,
          [cellKey]: {
            start_time: slot ? slot.inicio : timeKey,
            end_time: slot ? slot.termino : timeKey,
            reason: 'Restricción manual'
          }
        };
      }

      if (!prev[cellKey]) return prev;
      updated = true;
      const next = { ...prev };
      delete next[cellKey];
      return next;
    });

    if (updated) {
      setPendingSave(true);
    }
  };

  const toggleCell = (dayKey, timeKey) => {
    const shouldRestrict = getCellState(dayKey, timeKey) !== CELL_STATE.RESTRICTED;
    applyCellState(dayKey, timeKey, shouldRestrict);
  };

  const startDrag = (dayKey, timeKey) => {
    const currentlyRestricted = getCellState(dayKey, timeKey) === CELL_STATE.RESTRICTED;
    const mode = currentlyRestricted ? 'remove' : 'add';
    setDragMode(mode);
    setIsDragging(true);
    applyCellState(dayKey, timeKey, mode === 'add');
  };

  const dragOverCell = (dayKey, timeKey) => {
    if (!isDragging || !dragMode) return;
    applyCellState(dayKey, timeKey, dragMode === 'add');
  };

  const endDrag = () => {
    if (isDragging) {
      setIsDragging(false);
      setDragMode(null);
    }
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      setIsDragging(false);
      setDragMode(null);
    };
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, []);

  const preparePayload = () => {
    const byDay = {};

    Object.entries(cells).forEach(([cellKey, value]) => {
      const [dayKey, timeKey] = cellKey.split('_');
      if (!byDay[dayKey]) byDay[dayKey] = [];
      byDay[dayKey].push({ timeKey, value });
    });

    const payload = [];

    Object.entries(byDay).forEach(([dayKey, entries]) => {
      const sorted = entries
        .slice()
        .sort((a, b) => {
          const indexA = SLOT_INDEX_LOOKUP[a.timeKey];
          const indexB = SLOT_INDEX_LOOKUP[b.timeKey];
          return (typeof indexA === 'number' ? indexA : 0) - (typeof indexB === 'number' ? indexB : 0);
        });

      let group = [];

      const flush = () => {
        if (!group.length) return;
        const first = group[0];
        const last = group[group.length - 1];
        const reason = group.reduce((acc, item) => {
          const cellReason = item.value.reason || 'Restricción manual';
          return acc && acc !== cellReason ? 'Restricción manual' : cellReason;
        }, null) || 'Restricción manual';

        payload.push({
          professor_id: selectedProfessor.id,
          day: DAY_LABELS[dayKey] || dayKey,
          start_time: convertToBackendTime(first.value.start_time),
          end_time: convertToBackendTime(last.value.end_time),
          duration_blocks: group.length,
          reason
        });

        group = [];
      };

      sorted.forEach((entry, index) => {
        if (!group.length) {
          group.push(entry);
          if (index === sorted.length - 1) flush();
          return;
        }

        const previous = group[group.length - 1];
        const prevIndex = SLOT_INDEX_LOOKUP[previous.timeKey];
        const currentIndex = SLOT_INDEX_LOOKUP[entry.timeKey];
        const expected = (typeof prevIndex === 'number' ? prevIndex : -2) + 1;

        if (typeof currentIndex === 'number' && currentIndex === expected) {
          group.push(entry);
        } else {
          flush();
          group.push(entry);
        }

        if (index === sorted.length - 1) flush();
      });

      flush();
    });

    console.log('[restrictions] payload', payload);
    return payload;
  };

  const save = async () => {
    if (!selectedProfessor) return;

    const payload = preparePayload();
    setSaving(true);

    try {
      await axios.put(`${API_BASE}/assignments/restrictions/professor/${selectedProfessor.id}`, payload);
      setMessage({ type: 'success', text: 'Restricciones guardadas correctamente' });
      setPendingSave(false);
      loadRestrictionsCount();
      loadProfessorRestrictions(selectedProfessor.id);
    } catch (error) {
      console.error('[restrictions] failed saving payload', error);
      setMessage({ type: 'error', text: 'Error al guardar restricciones' });
    } finally {
      setSaving(false);
      setConfirmDialog(false);
    }
  };

  const clearAll = () => {
    setCells({});
    setPendingSave(true);
  };

  if (!selectedProfessor) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
          <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ScheduleIcon />
            Restricciones Profesores
          </Typography>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadProfessors}>
            Actualizar
          </Button>
        </Box>

        {loadingProfessors ? (
          <Box display="flex" justifyContent="center" py={8}>
            <CircularProgress size={56} />
          </Box>
        ) : (
          <Grid container spacing={2}>
            {professors.map((professor) => {
              const count = restrictionsCount[professor.id] || 0;
              return (
                <Grid item xs={12} sm={6} md={4} lg={3} key={professor.id}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                      '&:hover': { transform: 'translateY(-3px)', boxShadow: 4 }
                    }}
                    onClick={() => setSelectedProfessor(professor)}
                  >
                    <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Box display="flex" gap={2}>
                        <Avatar sx={{ bgcolor: 'primary.main', width: 42, height: 42 }}>
                          <PersonIcon />
                        </Avatar>
                        <Box flexGrow={1} minWidth={0}>
                          <Typography
                            variant="subtitle1"
                            sx={{
                              fontWeight: 600,
                              lineHeight: 1.2,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical'
                            }}
                            title={professor.nombre_completo}
                          >
                            {professor.nombre_completo}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Código: {professor.codigo}
                          </Typography>
                        </Box>
                      </Box>
                      <Chip
                        size="small"
                        color={count > 0 ? 'warning' : 'success'}
                        label={`${count} restricciones`}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        )}
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box display="flex" gap={2} alignItems="center">
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => {
              setSelectedProfessor(null);
              setCells({});
              setPendingSave(false);
            }}
          >
            Volver
          </Button>
          <Box>
            <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <PersonIcon />
              {selectedProfessor.nombre_completo}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Código: {selectedProfessor.codigo}
            </Typography>
          </Box>
        </Box>

        <Box display="flex" gap={1}>
          <Button variant="outlined" color="warning" startIcon={<ClearIcon />} onClick={clearAll}>
            Limpiar todo
          </Button>
          {pendingSave && (
            <Badge badgeContent="!" color="error">
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={() => setConfirmDialog(true)}
                disabled={saving}
              >
                Guardar cambios
              </Button>
            </Badge>
          )}
        </Box>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          • Haz clic o arrastra sobre celdas contiguas para alternar entre disponible y restricción.
        </Typography>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th
                style={{
                  textAlign: 'center',
                  padding: '12px 8px',
                  border: '1px solid #dcdcdc',
                  backgroundColor: '#f5f5f5',
                  minWidth: '110px'
                }}
              >
                INICIO
              </th>
              <th
                style={{
                  textAlign: 'center',
                  padding: '12px 8px',
                  border: '1px solid #dcdcdc',
                  backgroundColor: '#f5f5f5',
                  minWidth: '110px'
                }}
              >
                TÉRMINO
              </th>
              {DAYS.map((day) => (
                <th
                  key={day.key}
                  style={{
                    textAlign: 'center',
                    padding: '12px 8px',
                    border: '1px solid #dcdcdc',
                    backgroundColor: day.color,
                    minWidth: '120px'
                  }}
                >
                  {day.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {HORARIOS.map((slot) => (
              <tr key={slot.inicio}>
                <td
                  style={{
                    textAlign: 'center',
                    padding: '10px 6px',
                    border: '1px solid #dcdcdc',
                    backgroundColor: '#fafafa',
                    fontWeight: 600
                  }}
                >
                  {slot.inicio}
                </td>
                <td
                  style={{
                    textAlign: 'center',
                    padding: '10px 6px',
                    border: '1px solid #dcdcdc',
                    backgroundColor: '#fafafa',
                    fontWeight: 600
                  }}
                >
                  {slot.termino}
                </td>
                {DAYS.map((day) => {
                  const state = getCellState(day.key, slot.inicio);
                  const cellKey = `${day.key}_${slot.inicio}`;
                  const restricted = Boolean(cells[cellKey]);

                  return (
                    <td
                      key={cellKey}
                      style={{
                        border: '1px solid #dcdcdc',
                        padding: '6px',
                        cursor: 'pointer',
                        backgroundColor: restricted ? '#ffcdd2' : '#f8f9fa',
                        textAlign: 'center',
                        minHeight: '42px',
                        userSelect: 'none',
                        transition: 'background-color 0.15s ease-in-out',
                        boxShadow:
                          isDragging && dragMode === 'add' && !restricted
                            ? 'inset 0 0 0 2px rgba(244, 67, 54, 0.25)'
                            : 'none'
                      }}
                      onMouseDown={(event) => {
                        event.preventDefault();
                        startDrag(day.key, slot.inicio);
                      }}
                      onMouseEnter={() => dragOverCell(day.key, slot.inicio)}
                      onMouseUp={endDrag}
                    >
                      {state === CELL_STATE.RESTRICTED && (
                        <BlockIcon sx={{ fontSize: 18, color: 'error.main' }} />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Paper>

      <Dialog open={confirmDialog} onClose={() => setConfirmDialog(false)}>
        <DialogTitle>Confirmar guardado</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Deseas guardar las restricciones de {selectedProfessor?.nombre_completo}?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog(false)}>Cancelar</Button>
          <Button onClick={save} variant="contained" disabled={saving}>
            {saving ? <CircularProgress size={18} /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={4000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={message?.type || 'info'} onClose={() => setMessage(null)} sx={{ width: '100%' }}>
          {message?.text}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default ProfessorRestrictions;