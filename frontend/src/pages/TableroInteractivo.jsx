import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, CircularProgress, Alert, Snackbar,
  FormControl, InputLabel, Select, MenuItem, Stack,
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Divider
} from '@mui/material';
import {
  DndContext,
  useSensor,
  useSensors,
  PointerSensor
} from '@dnd-kit/core';
import { useDroppable } from '@dnd-kit/core';
import { useDraggable } from '@dnd-kit/core';
import axios from 'axios';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// --- COMPONENTES DND ---

const DroppableCell = ({ id, children }) => {
  const { isOver, setNodeRef } = useDroppable({ id });
  return (
    <Box
      ref={setNodeRef}
      sx={{
        width: '100%',
        height: '100%',
        minHeight: 110,
        backgroundColor: isOver ? '#e3f2fd' : 'transparent',
        transition: 'background-color 0.2s',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'stretch',
        alignItems: 'stretch',
        p: 0
      }}
    >
      {children}
    </Box>
  );
};

const DraggableCard = ({ id, data, loading, courseName, classroomName }) => {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id,
    data: data,
  });

  const { isFirst, isLast } = data;

  // Colores por tipo de clase
  const colorMap = {
    'T': { bg: '#e3f2fd', border: '#1976d2', text: '#0d47a1' }, // Teoría
    'P': { bg: '#e8f5e9', border: '#2e7d32', text: '#1b5e20' }, // Práctica
    'L': { bg: '#fff3e0', border: '#ed6c02', text: '#e65100' }  // Lab
  };
  const colors = colorMap[data.tipo] || { bg: '#f5f5f5', border: '#9e9e9e', text: '#212121' };

  return (
    <Box
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      sx={{
        width: '100%',
        height: '100%',
        minHeight: 110,
        backgroundColor: colors.bg,
        cursor: 'grab',
        opacity: isDragging || loading ? 0.6 : 1,
        borderLeft: `5px solid ${colors.border}`,
        borderTop: isFirst ? `1px solid ${colors.border}40` : 'none',
        borderBottom: isLast ? `1px solid ${colors.border}40` : 'none',
        borderRight: `1px solid ${colors.border}40`,
        borderTopLeftRadius: isFirst ? '4px' : 0,
        borderTopRightRadius: isFirst ? '4px' : 0,
        borderBottomLeftRadius: isLast ? '4px' : 0,
        borderBottomRightRadius: isLast ? '4px' : 0,
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        p: isFirst ? 1.5 : 0,
        overflow: 'hidden'
      }}
    >
      {isFirst ? (
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 700, color: colors.text, fontSize: '0.85rem', lineHeight: 1.2, mb: 0.5 }}>
            {courseName || data.course_code}
          </Typography>
          <Typography variant="caption" display="block" sx={{ color: '#555', fontWeight: 600 }}>
            Tipo: {data.tipo === 'T' ? 'Teoría' : data.tipo === 'P' ? 'Práctica' : 'Lab'}
          </Typography>
          <Typography variant="caption" display="block" sx={{ color: '#666', fontSize: '0.75rem' }}>
            Código: {data.course_code}
          </Typography>
          <Typography variant="caption" display="block" sx={{ color: '#666', fontSize: '0.75rem' }}>
            Aula: {data.classroom_id ? (classroomName || `Aula ${data.classroom_id}`) : 'Virtual'}
          </Typography>
        </Box>
      ) : null}
    </Box>
  );
};

export default function TableroInteractivo() {
  const [schedules, setSchedules] = useState([]);
  const [allProfessors, setAllProfessors] = useState({}); // id -> nombre_completo
  const [schedulesProfessors, setSchedulesProfessors] = useState([]); // Profesores con clases asignadas
  const [timeslots, setTimeslots] = useState({}); // id -> TimeslotInfo
  const [hoursList, setHoursList] = useState([]); // Listado de horas (1-16)
  const [coursesMap, setCoursesMap] = useState({}); // codigo -> nombre
  const [classroomsMap, setClassroomsMap] = useState({}); // id -> codigo

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [toast, setToast] = useState({ open: false, message: '', type: 'success' });
  const [jsonFiles, setJsonFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [selectedProfId, setSelectedProfId] = useState('');
  const [movingClasses, setMovingClasses] = useState(new Set());

  // Estado para el modal de error de restricciones
  const [conflictDialog, setConflictDialog] = useState({
    open: false,
    title: '',
    message: '',
    detail: null
  });

  useEffect(() => {
    initData();
  }, []);

  const initData = async () => {
    try {
      setLoading(true);
      
      // 1. Cargar Cursos de la BD para tener los nombres reales
      const coursesRes = await axios.get(`${API_BASE_URL}/api/courses`);
      const cMap = {};
      (coursesRes.data.courses || []).forEach(c => {
         cMap[c.codigo] = c.nombre;
      });
      setCoursesMap(cMap);

      // 2. Cargar Profesores de la BD
      const profRes = await axios.get(`${API_BASE_URL}/api/professors?limit=1000`);
      const profMap = {};
      (profRes.data.professors || []).forEach(p => {
        profMap[p.id] = p.nombre_completo;
      });
      setAllProfessors(profMap);

      // NUEVO: Cargar Aulas de la BD para mapear IDs a nombres comprensibles (Ej: G505)
      try {
        const classroomsRes = await axios.get(`${API_BASE_URL}/api/classrooms`);
        const clMap = {};
        (classroomsRes.data.classrooms || []).forEach(cl => {
           clMap[cl.id] = cl.codigo;
        });
        setClassroomsMap(clMap);
      } catch (err) {
        console.error("Error al cargar aulas:", err);
      }

      // 3. Cargar Timeslots de la BD
      const tsRes = await axios.get(`${API_BASE_URL}/api/time-slots`);
      const tsMap = {};
      const uniqueHours = {};
      
      (tsRes.data || []).forEach(ts => {
        tsMap[ts.id] = ts;
        if (ts.dia_semana === 1) {
           uniqueHours[ts.orden] = `${ts.hora_inicio} - ${ts.hora_fin}`;
        }
      });
      setTimeslots(tsMap);
      setHoursList(Object.entries(uniqueHours).map(([orden, hora]) => ({
        orden: parseInt(orden),
        hora
      })).sort((a,b) => a.orden - b.orden));

      // 4. Cargar lista de archivos de horario
      const filesRes = await axios.get(`${API_BASE_URL}/api/horario/archivos`);
      const allFiles = filesRes.data.files || [];
      const jsons = allFiles.filter(f => f.filename.endsWith('.json'));
      setJsonFiles(jsons);
      
      if (jsons.length > 0) {
        const latest = jsons[0].filename;
        setSelectedFile(latest);
        await loadScheduleData(latest, tsMap, profMap);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setError("Error inicializando datos");
      setLoading(false);
    }
  };

  const loadScheduleData = async (filename, currentTsMap = timeslots, currentProfMap = allProfessors) => {
    try {
      setLoading(true);
      // Agregar cache-buster query param para forzar la recarga real del archivo
      const res = await axios.get(`${API_BASE_URL}/api/horario/descargar/${filename}?t=${new Date().getTime()}`);
      const data = res.data;
      
      if (data && data.asignaciones) {
        // Mapear asignaciones EXPANDIÉNDOLAS a todos los timeslots que ocupan
        const mapped = [];
        data.asignaciones.forEach(a => {
           const sortedTids = [...a.timeslot_ids].sort((x, y) => x - y);
           sortedTids.forEach((tid, idx) => {
              const ts = currentTsMap[tid];
              if (ts) {
                 mapped.push({
                    // ID visual único por bloque timeslot para DnD-kit
                    id: `${a.section_id}-${tid}`,
                    section_id: a.section_id,
                    timeslot_id: tid,
                    course_code: a.course_code,
                    professor_id: a.professor_id,
                    classroom_id: a.classroom_id,
                    tipo: a.session_type,
                    timeslot_ids: sortedTids,
                    dia: ts.dia_semana,
                    franja: ts.orden,
                    isFirst: idx === 0,
                    isLast: idx === sortedTids.length - 1
                 });
              }
           });
        });
        setSchedules(mapped);

        // Extraer profesores únicos con asignaciones en este JSON
        const uniqueProfs = Array.from(new Set(data.asignaciones.map(m => m.professor_id)));
        const profsList = uniqueProfs.map(id => ({
           id,
           nombre: currentProfMap[id] || `Profesor ID: ${id}`
        })).sort((a, b) => a.nombre.localeCompare(b.nombre));

        setSchedulesProfessors(profsList);

        if (profsList.length > 0) {
           setSelectedProfId(prev => {
              if (uniqueProfs.includes(Number(prev))) return prev;
              return profsList[0].id;
           });
        } else {
           setSelectedProfId('');
        }
      }
    } catch (err) {
      console.error(err);
      setError("Error cargando el contenido del horario");
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const val = e.target.value;
    setSelectedFile(val);
    if (val) {
      loadScheduleData(val);
    }
  };

  const handleProfChange = (e) => {
    setSelectedProfId(e.target.value);
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    if (!over) return;
    
    const overId = String(over.id);
    if (!overId.startsWith('cell-')) return;
    
    const [_, diaStr, franjaStr] = overId.split('-');
    const nuevoDia = parseInt(diaStr.replace('dia', ''));
    const nuevaFranja = parseInt(franjaStr.replace('franja', ''));
    
    const claseId = active.data.current.section_id;
    const dragTimeslotId = active.data.current.timeslot_id;
    
    // Obtener información del timeslot arrastrado y el primero de la clase para calcular offset
    const dragTsInfo = timeslots[dragTimeslotId];
    const sortedTsIds = active.data.current.timeslot_ids;
    const firstTsId = sortedTsIds[0];
    const firstTsInfo = timeslots[firstTsId];
    
    const offset = (dragTsInfo && firstTsInfo) ? (dragTsInfo.orden - firstTsInfo.orden) : 0;
    let targetOrden = nuevaFranja - offset;
    if (targetOrden < 1) targetOrden = 1;

    setMovingClasses(prev => new Set(prev).add(claseId));

    try {
      // Buscar el ID del nuevo timeslot inicial correspondiente a nuevoDia y targetOrden
      const newTs = Object.values(timeslots).find(ts => ts.dia_semana === nuevoDia && ts.orden === targetOrden);
      if (!newTs) {
         setToast({ open: true, message: 'Franja horaria no válida en la BD.', type: 'error' });
         return;
      }

      // Fast-Track Validation pasando el archivo_origen
      const valRes = await axios.post(`${API_BASE_URL}/api/v1/horarios/validar-movimiento`, {
        clase_id: claseId,
        nuevo_dia: nuevoDia,
        nueva_franja_id: newTs.id,
        nueva_aula_id: active.data.current.classroom_id,
        archivo_origen: selectedFile
      });

      if (!valRes.data.valido) {
        setConflictDialog({
          open: true,
          title: 'Violación de Restricción Dura',
          message: valRes.data.mensaje || 'Este movimiento no está permitido por restricciones del sistema.',
          detail: valRes.data.detail
        });
      } else {
        // Confirmar movimiento pasando el archivo_origen
        await axios.put(`${API_BASE_URL}/api/v1/horarios/1/aplicar-movimiento`, {
          clase_id: claseId,
          nuevo_dia: nuevoDia,
          nueva_franja_id: newTs.id,
          nueva_aula_id: active.data.current.classroom_id,
          archivo_origen: selectedFile
        });
        
        // Volver a cargar el horario desde el servidor para reflejar la expansión y la persistencia real
        await loadScheduleData(selectedFile);
        
        let msj = 'Movimiento exitoso y guardado.';
        if (valRes.data.delta > 0) {
           msj += ` Advertencia: Costo de penalización aumentó +${valRes.data.delta.toFixed(2)}`;
        }
        setToast({ open: true, message: msj, type: valRes.data.delta > 0 ? 'warning' : 'success' });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Error al validar movimiento';
      setConflictDialog({
        open: true,
        title: 'Error de Red / Validación',
        message: errorMsg,
        detail: null
      });
    } finally {
      setMovingClasses(prev => {
        const n = new Set(prev);
        n.delete(claseId);
        return n;
      });
    }
  };

  const dias = [1, 2, 3, 4, 5, 6];
  const diaNombres = { 1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado' };

  // Filtrar schedules por el profesor seleccionado
  const filteredSchedules = schedules.filter(s => s.professor_id === Number(selectedProfId));

  const getSchedulesForCell = (dia, franja) => {
     return filteredSchedules.filter(s => s.dia === dia && s.franja === franja); 
  };

  // Renderizador de detalles de conflicto en el Modal
  const renderConflictDetail = () => {
    const { detail } = conflictDialog;
    if (!detail) return null;

    return (
      <Box sx={{ mt: 2, p: 2, backgroundColor: '#fff5f5', borderRadius: 1, border: '1px solid #ffcdd2' }}>
        <Typography variant="subtitle2" color="error.main" sx={{ fontWeight: 'bold', mb: 1 }}>
          Detalles Técnicos:
        </Typography>

        {/* Conflicto de Traslape de Profesor */}
        {detail.conflict_course_code && (
          <Box>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              <strong>Curso en Conflicto:</strong> {coursesMap[detail.conflict_course_code] || detail.conflict_course_code} ({detail.conflict_course_code})
            </Typography>
            {detail.classroom_id && (
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                <strong>Aula:</strong> {classroomsMap[detail.classroom_id] || `Aula ${detail.classroom_id}`}
              </Typography>
            )}
            {detail.overlap_slots && (
              <Typography variant="body2">
                <strong>Bloques Solapados:</strong> {detail.overlap_slots.map(s => {
                  const ts = timeslots[s];
                  return ts ? `${ts.hora_inicio}-${ts.hora_fin}` : `ID ${s}`;
                }).join(', ')}
              </Typography>
            )}
          </Box>
        )}

        {/* Conflicto de Disponibilidad de Profesor */}
        {detail.restriction && (
          <Box>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              <strong>Indisponibilidad Marcada:</strong>
            </Typography>
            <Typography variant="body2" sx={{ ml: 1, color: '#d32f2f' }}>
              Día: {diaNombres[detail.restriction.dia_semana] || 'N/A'}
            </Typography>
            <Typography variant="body2" sx={{ ml: 1, color: '#d32f2f' }}>
              Rango restringido: {detail.restriction.hora_inicio} a {detail.restriction.hora_fin}
            </Typography>
          </Box>
        )}

        {/* Conflicto de Capacidad de Aula */}
        {detail.capacidad !== undefined && (
          <Box>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              <strong>Capacidad Aula:</strong> {detail.capacidad} estudiantes.
            </Typography>
            <Typography variant="body2" color="error">
              <strong>Estudiantes Proyectados:</strong> {detail.alumnos_requeridos} alumnos (Excede capacidad).
            </Typography>
          </Box>
        )}
      </Box>
    );
  };

  if (loading && Object.keys(timeslots).length === 0) return <Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h4" sx={{ mb: 2, fontWeight: 700, color: '#1e1e2d' }}>
        Tablero de Ajuste Manual (Human-in-the-Loop)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Selecciona un horario generado e interactúa directamente en el horario del docente (Drag and Drop).
      </Typography>
      
      <Stack direction="row" spacing={3} sx={{ mb: 4 }}>
        <FormControl sx={{ minWidth: 320 }}>
          <InputLabel id="horario-select-label">1. Seleccionar Horario Generado</InputLabel>
          <Select
            labelId="horario-select-label"
            value={selectedFile}
            label="1. Seleccionar Horario Generado"
            onChange={handleFileChange}
          >
            {jsonFiles.map(f => (
              <MenuItem key={f.filename} value={f.filename}>
                {f.filename}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 320 }} disabled={schedulesProfessors.length === 0}>
          <InputLabel id="prof-select-label">2. Seleccionar Profesor</InputLabel>
          <Select
            labelId="prof-select-label"
            value={selectedProfId}
            label="2. Seleccionar Profesor"
            onChange={handleProfChange}
          >
            {schedulesProfessors.map(p => (
              <MenuItem key={p.id} value={p.id}>
                {p.nombre}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <Box sx={{ overflowX: 'auto', border: '1px solid #e0e0e0', borderRadius: 2, backgroundColor: '#fff', p: 2 }}>
          <Grid container sx={{ minWidth: 1000 }}>
            {/* Header del Grid */}
            <Grid item xs={12} sx={{ display: 'flex', borderBottom: '2px solid #ccc', pb: 1, mb: 1 }}>
              <Box sx={{ width: 160, fontWeight: 700, color: '#555', textAlign: 'center' }}>Hora / Bloque</Box>
              {dias.map(d => (
                <Box key={d} sx={{ flex: 1, fontWeight: 700, color: '#333', textAlign: 'center' }}>
                  {diaNombres[d]}
                </Box>
              ))}
            </Grid>
            
            {/* Filas de horas */}
            {hoursList.map(h => (
              <Grid item xs={12} key={h.orden} sx={{ display: 'flex', borderBottom: '1px solid #e0e0e0', minHeight: 110 }}>
                {/* Eje Izquierdo: Horas */}
                <Box sx={{ width: 160, pr: 2, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f9f9f9', borderRight: '1px solid #e0e0e0' }}>
                  <Typography variant="body1" sx={{ fontWeight: 700, color: '#333', fontSize: '0.95rem', textAlign: 'center' }}>
                    {h.hora}
                  </Typography>
                </Box>

                {/* Celdas del Tablero (Lunes - Sábado) */}
                {dias.map(d => (
                  <Box key={`${d}-${h.orden}`} sx={{ flex: 1, borderRight: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column', alignItems: 'stretch', justifyContent: 'stretch' }}>
                    <DroppableCell id={`cell-dia${d}-franja${h.orden}`}>
                      {getSchedulesForCell(d, h.orden).map(s => (
                        <DraggableCard 
                          key={s.id} 
                          id={`card-${s.id}`} 
                          data={s} 
                          loading={movingClasses.has(s.section_id)}
                          courseName={coursesMap[s.course_code]}
                          classroomName={classroomsMap[s.classroom_id]}
                        />
                      ))}
                    </DroppableCell>
                  </Box>
                ))}
              </Grid>
            ))}
          </Grid>
        </Box>
      </DndContext>

      {/* Snackbar para notificaciones exitosas */}
      <Snackbar
        open={toast.open}
        autoHideDuration={6000}
        onClose={() => setToast({...toast, open: false})}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={toast.type} onClose={() => setToast({...toast, open: false})}>
          {toast.message}
        </Alert>
      </Snackbar>

      {/* DIÁLOGO CENTRAL DE ERROR / CONFLICTO */}
      <Dialog
        open={conflictDialog.open}
        onClose={() => setConflictDialog({ ...conflictDialog, open: false })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5, color: '#d32f2f', fontWeight: 'bold' }}>
          <ErrorOutlineIcon color="error" fontSize="large" />
          {conflictDialog.title}
        </DialogTitle>
        <Divider />
        <DialogContent sx={{ py: 3 }}>
          <Typography variant="body1" sx={{ fontWeight: 500, color: '#2c3e50', mb: 2 }}>
            {conflictDialog.message}
          </Typography>
          {renderConflictDetail()}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button 
            variant="contained" 
            color="error" 
            onClick={() => setConflictDialog({ ...conflictDialog, open: false })}
            fullWidth
          >
            Entendido
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
