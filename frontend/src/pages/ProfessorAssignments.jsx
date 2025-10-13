import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Snackbar,
  Stack,
  TextField,
  Tooltip,
  Typography
} from '@mui/material';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';

import { assignmentsAPI } from '../api/assignmentsAPI';
import { professorsAPI } from '../api/professorsAPI';

const SESSION_LABELS = {
  T: 'Teoría',
  P: 'Práctica',
  L: 'Laboratorio'
};

const DEFAULT_SEMESTER = '2025-20';
const SESSION_ORDER = { T: 0, P: 1, L: 2 };
const SESSION_DISPLAY_ORDER = ['T', 'P', 'L'];

const ProfessorAssignments = () => {
  const [loading, setLoading] = useState(true);
  const [professors, setProfessors] = useState([]);
  const [courses, setCourses] = useState([]);
  const [selections, setSelections] = useState({});
  const [savingCourseId, setSavingCourseId] = useState(null);
  const [message, setMessage] = useState(null);

  const professorOptions = useMemo(
    () =>
      professors.map((prof) => ({
        id: prof.id,
        label: `${prof.codigo ? `${prof.codigo} · ` : ''}${prof.nombre_completo}`
      })),
    [professors]
  );

  useEffect(() => {
    loadData();
  }, []);

  // Limpiar selecciones inválidas cuando cambian los cursos
  useEffect(() => {
    if (courses.length === 0) return;

    setSelections((prevSelections) => {
      const cleanedSelections = { ...prevSelections };
      let hasChanges = false;

      courses.forEach((course) => {
        const validSlots = new Set();
        
        if (course.leagues && course.leagues.length > 0) {
          course.leagues.forEach(league => {
            (league.sessions || []).forEach(session => {
              validSlots.add(`${session.session_type}-${league.league}`);
            });
          });
        } else if (course.session_types && course.session_types.length > 0) {
          course.session_types.forEach(session => {
            validSlots.add(`${session.session_type}-1`);
          });
        }

        const courseSelections = cleanedSelections[course.id] || {};
        const newCourseSelections = {};

        Object.entries(courseSelections).forEach(([leagueKey, sessionMap]) => {
          Object.entries(sessionMap || {}).forEach(([sessionType, professorIds]) => {
            const slotKey = `${sessionType}-${leagueKey}`;
            if (validSlots.has(slotKey)) {
              if (!newCourseSelections[leagueKey]) {
                newCourseSelections[leagueKey] = {};
              }
              newCourseSelections[leagueKey][sessionType] = professorIds;
            } else {
              hasChanges = true;
            }
          });
        });

        cleanedSelections[course.id] = newCourseSelections;
      });

      return hasChanges ? cleanedSelections : prevSelections;
    });
  }, [courses]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [professorsResponse, coursesResponse] = await Promise.all([
        professorsAPI.getProfessors(),
        assignmentsAPI.getCoursesWithAssignments()
      ]);

      setProfessors(professorsResponse.professors || []);
      const sortedCourses = [...(coursesResponse || [])].sort((a, b) => {
        const cicloA = a.ciclo ?? 0;
        const cicloB = b.ciclo ?? 0;
        if (cicloA !== cicloB) {
          return cicloA - cicloB;
        }
        return (a.codigo || '').localeCompare(b.codigo || '');
      });
      setCourses(sortedCourses);

      // Construir selecciones REACTIVAS basadas en la estructura actual de secciones
      const initialSelections = {};
      sortedCourses.forEach((course) => {
        const courseSelections = {};
        
        // Construir mapa de capacidades por (sessionType, league) desde leagues o session_types
        const validSlots = new Set();
        if (course.leagues && course.leagues.length > 0) {
          // Usar leagues si están disponibles
          course.leagues.forEach(league => {
            (league.sessions || []).forEach(session => {
              validSlots.add(`${session.session_type}-${league.league}`);
            });
          });
        } else if (course.session_types && course.session_types.length > 0) {
          // Fallback: usar session_types con league 1 por defecto
          course.session_types.forEach(session => {
            validSlots.add(`${session.session_type}-1`);
          });
        }

        // Filtrar assignments existentes y mantener solo los válidos
        (course.assignments || []).forEach((assignment) => {
          const leagueKey = String(assignment.league ?? 1);
          const slotKey = `${assignment.session_type}-${leagueKey}`;
          
          // Solo incluir si el slot es válido según la configuración actual
          if (validSlots.has(slotKey)) {
            if (!courseSelections[leagueKey]) {
              courseSelections[leagueKey] = {};
            }
            if (!courseSelections[leagueKey][assignment.session_type]) {
              courseSelections[leagueKey][assignment.session_type] = [];
            }
            if (!courseSelections[leagueKey][assignment.session_type].includes(assignment.professor_id)) {
              courseSelections[leagueKey][assignment.session_type].push(assignment.professor_id);
            }
          }
        });
        
        initialSelections[course.id] = courseSelections;
      });
      setSelections(initialSelections);
    } catch (error) {
      console.error('[assignments] failed to load data', error);
      setMessage({ type: 'error', text: 'Error cargando información de cursos y profesores' });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectionChange = (courseId, league, sessionType, newValues, maxSelections) => {
    setSelections((prev) => {
      const next = { ...prev };
      const trimmed = newValues.slice(0, maxSelections);
      const courseSelections = { ...(next[courseId] || {}) };
      const leagueKey = String(league);
      const leagueSelections = { ...(courseSelections[leagueKey] || {}) };
      leagueSelections[sessionType] = trimmed.map((option) => option.id);
      courseSelections[leagueKey] = leagueSelections;
      next[courseId] = courseSelections;
      return next;
    });
  };

  const handleSave = async (course) => {
    const currentSelections = selections[course.id] || {};
    const payloadAssignments = [];

    Object.entries(currentSelections).forEach(([leagueKey, sessionMap]) => {
      Object.entries(sessionMap || {}).forEach(([sessionType, professorIds]) => {
        (professorIds || []).forEach((professorId) => {
          payloadAssignments.push({
            professor_id: professorId,
            session_type: sessionType,
            league: Number(leagueKey)
          });
        });
      });
    });

    setSavingCourseId(course.id);
    try {
      await assignmentsAPI.updateCourseAssignments(course.id, {
        assignments: payloadAssignments,
        semestre: DEFAULT_SEMESTER
      });
      setMessage({ type: 'success', text: `Asignaciones de ${course.codigo} actualizadas` });
      await loadData();
    } catch (error) {
      console.error('[assignments] failed to save', error);
      const errorMessage = error?.response?.data?.detail || 'No se pudo guardar la asignación';
      setMessage({ type: 'error', text: errorMessage });
    } finally {
      setSavingCourseId(null);
    }
  };

  const renderSessionSelector = (course, league, session) => {
    const leagueSelections = selections[course.id]?.[String(league)] || {};
    const selectedIds = leagueSelections[session.session_type] || [];
    const selectedOptions = professorOptions.filter((option) => selectedIds.includes(option.id));
    const fallbackGroupCounts = {
      T: course.grupos_teoria || 0,
      P: course.grupos_practica || 0,
      L: course.grupos_laboratorio || 0
    };
    const maxSelections = Math.max(
      session.section_count || fallbackGroupCounts[session.session_type] || 1,
      1
    );
    const sectionDetails = session.section_details || [];
    const tooltipContent = sectionDetails.length
      ? sectionDetails
          .map((detail) =>
            detail.nrc ? `${detail.seccion} (NRC: ${detail.nrc})` : detail.seccion
          )
          .join(', ')
      : (session.sections || []).join(', ');

    // Key única que incluye la cantidad de secciones para forzar re-render cuando cambie
    const uniqueKey = `${course.id}-${league}-${session.session_type}-${session.section_count}-${(session.sections || []).join('-')}`;

    return (
      <Box key={uniqueKey} sx={{ mt: 2 }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography variant="subtitle2" sx={{ minWidth: 140 }}>
            {SESSION_LABELS[session.session_type] || session.label}
          </Typography>
          <Chip
            size="small"
            color="info"
            label={`${session.section_count} sección${session.section_count === 1 ? '' : 'es'}`}
          />
          {tooltipContent ? (
            <Tooltip title={`Secciones activas: ${tooltipContent}`}>
              <Chip size="small" variant="outlined" label="Detalles" />
            </Tooltip>
          ) : null}
        </Stack>
        <Autocomplete
          key={uniqueKey}
          multiple
          options={professorOptions}
          value={selectedOptions}
          onChange={(_, newValue) =>
            handleSelectionChange(course.id, league, session.session_type, newValue, maxSelections)
          }
          disableCloseOnSelect
          isOptionEqualToValue={(option, value) => option.id === value.id}
          getOptionLabel={(option) => option?.label || ''}
          sx={{ mt: 1, maxWidth: 420 }}
          renderTags={(value, getTagProps) =>
            value.map((option, index) => (
              <Chip
                {...getTagProps({ index })}
                key={option.id}
                label={option.label}
                size="small"
                color="primary"
                variant="outlined"
              />
            ))
          }
          renderInput={(params) => (
            <TextField
              {...params}
              label={`Selecciona hasta ${maxSelections}`}
              placeholder="Seleccionar profesor"
              size="small"
            />
          )}
        />
      </Box>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress size={64} />
      </Box>
    );
  }

  return (
    <Box sx={{ px: 1 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PersonAddAltIcon />
            Asignación de Profesores
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Selecciona los docentes responsables por tipo de sesión. El límite por tipo está marcado por la
            cantidad de secciones activas.
          </Typography>
        </Box>
        <Button startIcon={<RefreshIcon />} variant="outlined" onClick={loadData}>
          Refrescar
        </Button>
      </Box>

      {courses.length === 0 ? (
        <Alert severity="info">No se encontraron cursos activos.</Alert>
      ) : (
        <Grid container spacing={2}>
          {courses.map((course) => {
            const courseLeagues = course.leagues || [];

            return (
              <Grid item xs={12} md={6} key={course.id}>
                <Card elevation={1}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                      <Box>
                        <Typography variant="h6">{course.codigo}</Typography>
                        <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>
                          {course.nombre}
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                          <Chip label={`Ciclo ${course.ciclo}`} size="small" />
                          {course.creditos ? (
                            <Chip label={`${course.creditos} créditos`} size="small" color="primary" />
                          ) : null}
                          {course.modalidad ? (
                            (() => {
                              const modalidadValue = String(course.modalidad || '').toUpperCase();
                              const isRemote = ['NPR', 'NO_PRESENCIAL'].includes(modalidadValue);
                              return (
                                <Chip
                                  label={isRemote ? 'No presencial' : 'Presencial'}
                                  size="small"
                                  color={isRemote ? 'secondary' : 'default'}
                                />
                              );
                            })()
                          ) : null}
                          <Chip
                            label={`T:${course.grupos_teoria || 0}`}
                            size="small"
                            color={(course.grupos_teoria || 0) > 0 ? 'success' : 'default'}
                          />
                          <Chip
                            label={`P:${course.grupos_practica || 0}`}
                            size="small"
                            color={(course.grupos_practica || 0) > 0 ? 'info' : 'default'}
                          />
                          <Chip
                            label={`L:${course.grupos_laboratorio || 0}`}
                            size="small"
                            color={(course.grupos_laboratorio || 0) > 0 ? 'warning' : 'default'}
                          />
                        </Stack>
                      </Box>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={
                          savingCourseId === course.id ? <CircularProgress color="inherit" size={16} /> : <SaveIcon />
                        }
                        onClick={() => handleSave(course)}
                        disabled={savingCourseId === course.id}
                      >
                        Guardar
                      </Button>
                    </Stack>

                    {(course.session_types || []).length === 0 && courseLeagues.length === 0 ? (
                      <Alert severity="warning" sx={{ mt: 2 }}>
                        Este curso no tiene secciones activas configuradas.
                      </Alert>
                    ) : (
                      <Stack spacing={3} sx={{ mt: 2 }}>
                        {courseLeagues.length > 0
                          ? courseLeagues.map((leagueDetail) => (
                              <Box key={`${course.id}-league-${leagueDetail.league}`}>
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                  Liga {leagueDetail.league}
                                </Typography>
                                <Stack spacing={2} sx={{ mt: 1 }}>
                                  {(leagueDetail.sessions || []).map((session) =>
                                    renderSessionSelector(course, leagueDetail.league, session)
                                  )}
                                </Stack>
                              </Box>
                            ))
                          : [...(course.session_types || [])]
                              .sort(
                                (a, b) =>
                                  (SESSION_ORDER[a.session_type] ?? 99) - (SESSION_ORDER[b.session_type] ?? 99)
                              )
                              .map((session) => renderSessionSelector(course, 1, session))}
                      </Stack>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={5000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {message ? <Alert severity={message.type}>{message.text}</Alert> : null}
      </Snackbar>
    </Box>
  );
};

export default ProfessorAssignments;
