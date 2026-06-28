import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Alert,
  AlertTitle,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Paper,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
  IconButton,
  Collapse
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Download as DownloadIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Description as FileIcon,
  Refresh as RefreshIcon,
  History as HistoryIcon,
  Assessment as AssessmentIcon,
  Code as CodeIcon,
  TableView as TableViewIcon,
  Terminal as TerminalIcon,
  ContentCopy as CopyIcon,
  Analytics as AnalyticsIcon,
  ClearAll as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Check as SuccessIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function GenerarHorario() {
  const [status, setStatus] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [files, setFiles] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [error, setError] = useState(null);
  const [loadingExecutions, setLoadingExecutions] = useState(false);
  const [showTelemetry, setShowTelemetry] = useState(true);
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  
  const consoleContainerRef = useRef(null);

  // Auto-scroll telemetry logs inside the container without affecting page scroll
  useEffect(() => {
    if (autoScroll && consoleContainerRef.current) {
      const container = consoleContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  }, [status?.logs, autoScroll]);

  // Poll status when generating (Optimizado a 1000ms para mayor fluidez)
  useEffect(() => {
    if (isGenerating) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/api/horario/status`);
          setStatus(response.data);
          
          // Stop polling if generation completed or failed/cancelled
          if (!response.data.is_running) {
            setIsGenerating(false);
            loadFiles();
            loadExecutions(); // Reload executions when one finishes
            
            // Auto-download if successful
            if (response.data.filename && !response.data.error) {
              downloadFile(response.data.filename);
            }
          }
        } catch (err) {
          console.error('Error checking status:', err);
        }
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [isGenerating]);

  // Load available files, executions, and check current status on mount
  useEffect(() => {
    loadFiles();
    loadExecutions();
    checkCurrentStatus();
  }, []);

  const checkCurrentStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/horario/status`);
      if (response.data && response.data.is_running) {
        setStatus(response.data);
        setIsGenerating(true);
      } else if (response.data && response.data.logs?.length > 0) {
        setStatus(response.data);
      }
    } catch (err) {
      console.error('Error checking initial status:', err);
    }
  };

  const loadFiles = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/horario/archivos`);
      setFiles(response.data.files || []);
    } catch (err) {
      console.error('Error loading files:', err);
    }
  };

  const loadExecutions = async () => {
    setLoadingExecutions(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/algorithm/executions?limit=5`);
      setExecutions(response.data || []);
    } catch (err) {
      console.error('Error loading executions:', err);
    } finally {
      setLoadingExecutions(false);
    }
  };

  const startGeneration = async () => {
    setError(null);
    setIsGenerating(true);
    setShowTelemetry(true);
    
    try {
      await axios.post(`${API_BASE_URL}/api/horario/generar`);
      setStatus({
        is_running: true,
        progress: 0,
        message: 'Iniciando generación...',
        started_at: new Date().toISOString(),
        logs: ['[INFO] Generación iniciada por el usuario desde la UI.'],
        metrics: {
          iterations: [],
          repaired_count: 0,
          total_sections: 298,
          assigned_sections: 0,
          elapsed_time: 0.0,
          best_cost: null
        }
      });
    } catch (err) {
      setError(err.response?.data?.error || 'Error al iniciar la generación');
      setIsGenerating(false);
    }
  };

  const cancelGeneration = async () => {
    setCancelling(true);
    try {
      await axios.post(`${API_BASE_URL}/api/horario/cancelar`);
      setIsGenerating(false);
      setStatus((prev) => prev ? { ...prev, is_running: false, error: 'Generación detenida manualmente por el usuario.' } : null);
    } catch (err) {
      console.error('Error al cancelar la generación:', err);
    } finally {
      setCancelling(false);
    }
  };

  const downloadFile = (filename) => {
    const url = `${API_BASE_URL}/api/horario/descargar/${filename}`;
    window.open(url, '_blank');
  };

  const copyLogs = () => {
    if (status?.logs) {
      navigator.clipboard.writeText(status.logs.join('\n'));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const clearTelemetry = () => {
    if (!isGenerating) {
      setStatus(null);
    }
  };

  // Helper to determine the status of each step in the optimization pipeline
  const getStepStatus = (stepIndex) => {
    const progress = status?.progress || 0;
    
    switch (stepIndex) {
      case 0: // Grafo & GNN
        if (progress >= 25) return { completed: true, active: false };
        if (progress > 0) return { completed: false, active: true };
        return { completed: false, active: false };
      case 1: // Colonia de Hormigas
        if (progress >= 85) return { completed: true, active: false };
        if (progress >= 25) return { completed: false, active: true };
        return { completed: false, active: false };
      case 2: // Reparación Greedy
        if (progress >= 95) return { completed: true, active: false };
        if (progress >= 85) return { completed: false, active: true };
        return { completed: false, active: false };
      case 3: // Exportación
        if (progress === 100) return { completed: true, active: false };
        if (progress >= 95) return { completed: false, active: true };
        return { completed: false, active: false };
      default:
        return { completed: false, active: false };
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScheduleIcon sx={{ fontSize: 36, color: '#1976d2' }} />
          Generar Horario
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Genera el horario completo usando el algoritmo híbrido <strong>ACO + GraphSAGE con Reparación Greedy</strong> y descarga el archivo Excel con los horarios.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Left Column: Actions, Progress, and Telemetry */}
        <Grid item xs={12} md={7}>
          {/* Main Action Card */}
          <Card sx={{ mb: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                <PlayIcon color="primary" /> Nueva Generación
              </Typography>
              
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <AlertTitle>Error</AlertTitle>
                  {error}
                </Alert>
              )}

              {status && status.error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <AlertTitle>Ejecución Detenida</AlertTitle>
                  {status.error}
                </Alert>
              )}

              {status && status.filename && !status.error && (
                <Alert severity="success" sx={{ mb: 2 }} icon={<CheckIcon />}>
                  <AlertTitle>¡Generación Completada!</AlertTitle>
                  Archivo generado: <strong>{status.filename}</strong>
                  <br />
                  Se aplicó la fase de <strong>Reparación Greedy</strong> para garantizar máxima cobertura.
                </Alert>
              )}

              {/* Progress Bar */}
              {isGenerating && (
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }} color="primary">
                      {status?.message || 'Procesando...'}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }} color="primary">
                      {status?.progress || 0}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={status?.progress || 0}
                    sx={{ height: 10, borderRadius: 1, backgroundColor: '#e3f2fd' }}
                  />
                </Box>
              )}

              <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <PlayIcon />}
                  onClick={startGeneration}
                  disabled={isGenerating}
                  sx={{ flexGrow: 1, py: 1.5, fontSize: '1.1rem', fontWeight: 600, textTransform: 'none', borderRadius: 2 }}
                >
                  {isGenerating ? 'Generando Horario...' : 'Generar Horario Completo (ACO + GraphSAGE)'}
                </Button>
                {isGenerating && (
                  <Button
                    variant="outlined"
                    color="error"
                    size="large"
                    startIcon={cancelling ? <CircularProgress size={20} color="inherit" /> : <StopIcon />}
                    onClick={cancelGeneration}
                    disabled={cancelling}
                    sx={{ px: 3, fontWeight: 600, textTransform: 'none', borderRadius: 2 }}
                  >
                    {cancelling ? 'Deteniendo...' : 'Detener'}
                  </Button>
                )}
              </Box>

              <Box sx={{ mt: 3, p: 2, backgroundColor: '#f8faff', borderRadius: 2, border: '1px solid #e3f2fd' }}>
                <Typography variant="subtitle2" sx={{ color: '#1976d2', fontWeight: 600, mb: 1 }}>
                  Etapas del Algoritmo Híbrido:
                </Typography>
                <Grid container spacing={1}>
                  {[
                    { title: '1. Construcción de Grafo', desc: 'Mapeo de restricciones físicas y pedagógicas' },
                    { title: '2. Heurística Neural GraphSAGE', desc: 'Sugerencias inteligentes de asignación' },
                    { title: '3. Colonia de Hormigas (ACO)', desc: 'Exploración metaheurística de soluciones' },
                    { title: '4. Reparación Greedy', desc: 'Garantiza el 100% de secciones asignadas sin cruces' }
                  ].map((step, idx) => (
                    <Grid item xs={12} sm={6} key={idx}>
                      <Paper variant="outlined" sx={{ p: 1, height: '100%', backgroundColor: '#fff' }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', color: '#1976d2' }}>
                          {step.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {step.desc}
                        </Typography>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            </CardContent>
          </Card>

          {/* TELEMETRY CARD (Transparent Optimizer Insights) */}
          {status && (status.is_running || status.logs?.length > 0) && (
            <Card sx={{ mb: 3, borderLeft: '4px solid #1976d2', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
              <CardContent sx={{ pb: 2 }}>
                {/* Telemetry Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TerminalIcon color="primary" /> Telemetría de la Optimización
                    {isGenerating && <CircularProgress size={16} sx={{ ml: 1 }} />}
                  </Typography>
                  <Box>
                    <IconButton size="small" onClick={copyLogs} title="Copiar logs al portapapeles">
                      {copied ? <SuccessIcon fontSize="small" color="success" /> : <CopyIcon fontSize="small" />}
                    </IconButton>
                    {!isGenerating && (
                      <IconButton size="small" onClick={clearTelemetry} title="Limpiar telemetría">
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    )}
                    <IconButton size="small" onClick={() => setShowTelemetry(!showTelemetry)}>
                      {showTelemetry ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </Box>
                </Box>

                <Collapse in={showTelemetry}>
                  {/* Pipeline Step Checklist */}
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: 'text.secondary' }}>
                      Estado del Pipeline de Ejecución:
                    </Typography>
                    <Grid container spacing={2}>
                      {[
                        'Carga de Grafo & GNN',
                        'Colonia de Hormigas',
                        'Reparación Greedy',
                        'Exportación Excel'
                      ].map((stepLabel, idx) => {
                        const stepStat = getStepStatus(idx);
                        return (
                          <Grid item xs={12} sm={6} md={3} key={idx}>
                            <Paper
                              variant="outlined"
                              sx={{
                                p: 1,
                                textAlign: 'center',
                                borderColor: stepStat.completed ? '#4caf50' : stepStat.active ? '#1976d2' : '#e0e0e0',
                                backgroundColor: stepStat.completed ? '#f1f8e9' : stepStat.active ? '#e3f2fd' : '#fafafa',
                                transition: 'all 0.3s ease'
                              }}
                            >
                              <Box display="flex" justifyContent="center" alignItems="center" gap={0.5}>
                                {stepStat.completed ? (
                                  <CheckIcon fontSize="inherit" color="success" />
                                ) : stepStat.active ? (
                                  <CircularProgress size={10} thickness={6} />
                                ) : (
                                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#bdbdbd' }} />
                                )}
                                <Typography variant="caption" sx={{ fontWeight: stepStat.active || stepStat.completed ? 600 : 400 }}>
                                  {stepLabel}
                                </Typography>
                              </Box>
                            </Paper>
                          </Grid>
                        );
                      })}
                    </Grid>
                  </Box>

                  {/* Real-time Telemetry Metrics Cards */}
                  {status?.metrics && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: 'text.secondary' }}>
                        Métricas en Tiempo Real:
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6} sm={3}>
                          <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                            <Typography variant="caption" color="text.secondary">Mejor Costo</Typography>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#1976d2' }}>
                              {status.metrics.best_cost !== null && status.metrics.best_cost !== undefined
                                ? status.metrics.best_cost.toFixed(2)
                                : '-'}
                            </Typography>
                          </Paper>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                            <Typography variant="caption" color="text.secondary">Secciones Asignadas</Typography>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                              {status.metrics.assigned_sections || 0}
                              <span style={{ fontSize: '0.75rem', color: '#666', fontWeight: 400 }}>
                                /{status.metrics.total_sections || 298}
                              </span>
                            </Typography>
                          </Paper>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                            <Typography variant="caption" color="text.secondary">Reparadas Greedy</Typography>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#ff9800' }}>
                              {status.metrics.repaired_count || 0}
                            </Typography>
                          </Paper>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Paper variant="outlined" sx={{ p: 1.5, textAlign: 'center' }}>
                            <Typography variant="caption" color="text.secondary">Tiempo de Cómputo</Typography>
                            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                              {status.metrics.elapsed_time > 0
                                ? `${status.metrics.elapsed_time.toFixed(1)}s`
                                : isGenerating
                                  ? `${Math.round((new Date() - new Date(status.started_at)) / 1000)}s`
                                  : '-'}
                            </Typography>
                          </Paper>
                        </Grid>
                      </Grid>
                    </Box>
                  )}

                  {/* Terminal Log Console */}
                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                        Logs del Proceso (Consola Transparente):
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="caption" sx={{ color: 'text.secondary', cursor: 'pointer', display: 'flex', alignItems: 'center' }} onClick={() => setAutoScroll(!autoScroll)}>
                          <input 
                            type="checkbox" 
                            checked={autoScroll} 
                            onChange={(e) => setAutoScroll(e.target.checked)} 
                            style={{ marginRight: '4px', cursor: 'pointer' }}
                          />
                          Auto-scroll consola
                        </Typography>
                      </Box>
                    </Box>
                    <Box 
                      ref={consoleContainerRef}
                      sx={{ 
                        backgroundColor: '#121212', 
                        color: '#33ff33', 
                        fontFamily: 'Consolas, monospace', 
                        p: 2, 
                        borderRadius: 2, 
                        maxHeight: 400, 
                        overflowY: 'auto', 
                        fontSize: '0.8rem',
                        border: '1px solid #333',
                        boxShadow: 'inset 0 0 10px rgba(0,0,0,0.8)',
                        '&::-webkit-scrollbar': {
                          width: '6px',
                          height: '6px'
                        },
                        '&::-webkit-scrollbar-track': {
                          background: '#121212'
                        },
                        '&::-webkit-scrollbar-thumb': {
                          background: '#444',
                          borderRadius: '4px'
                        },
                        '&::-webkit-scrollbar-thumb:hover': {
                          background: '#666'
                        }
                      }}
                    >
                      {status?.logs && status.logs.map((log, index) => {
                        let color = '#e0e0e0';
                        if (log.includes('[OK]')) color = '#4caf50';
                        else if (log.includes('[WARN]') || log.includes('[PENDIENTE]')) color = '#ff9800';
                        else if (log.includes('[X]') || log.includes('[ERROR]') || log.includes('[ERR]')) color = '#f44336';
                        else if (log.includes('[CRITICO]')) color = '#e040fb';
                        else if (log.includes('Iteración')) color = '#2196f3';
                        else if (log.includes('[REPARACIÓN]')) color = '#00bcd4';
                        else if (log.includes('[EXCEL]') || log.includes('[GUARDADO]')) color = '#9c27b0';
                        else if (log.includes('Construyendo grafo') || log.includes('Creando nodos') || log.includes('Creando aristas') || log.includes('Grafo construido')) color = '#00e676';
                        
                        return (
                          <div key={index} style={{ color, marginBottom: '3px', whiteSpace: 'pre-wrap', lineHeight: '1.2rem' }}>
                            <span style={{ color: '#666', marginRight: '6px', userSelect: 'none' }}>[{index + 1}]</span>
                            {log}
                          </div>
                        );
                      })}
                      {(!status?.logs || status.logs.length === 0) && (
                        <div style={{ color: '#888', fontStyle: 'italic' }}>Esperando salida...</div>
                      )}
                    </Box>
                  </Box>

                  {/* Convergence Table */}
                  {status?.metrics?.iterations && status.metrics.iterations.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <AnalyticsIcon fontSize="small" /> Evolución de Costos por Iteración ACO:
                      </Typography>
                      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1.5 }}>
                        <Table size="small">
                          <TableHead sx={{ backgroundColor: '#f5f5f5' }}>
                            <TableRow>
                              <TableCell sx={{ fontWeight: 600, py: 0.75 }}>Iteración</TableCell>
                              <TableCell sx={{ fontWeight: 600, py: 0.75 }}>Mejor de Iteración</TableCell>
                              <TableCell sx={{ fontWeight: 600, py: 0.75 }}>Costo Promedio</TableCell>
                              <TableCell sx={{ fontWeight: 600, py: 0.75 }}>Mejor Global</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {status.metrics.iterations.map((it) => (
                              <TableRow key={it.iteration} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                <TableCell sx={{ py: 0.75 }}>Iteración #{it.iteration}</TableCell>
                                <TableCell sx={{ py: 0.75, color: '#1976d2', fontWeight: 600 }}>{it.best.toFixed(2)}</TableCell>
                                <TableCell sx={{ py: 0.75 }}>{it.avg.toFixed(2)}</TableCell>
                                <TableCell sx={{ py: 0.75, color: '#2e7d32', fontWeight: 600 }}>{it.global.toFixed(2)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  )}
                </Collapse>
              </CardContent>
            </Card>
          )}

          {/* Execution History Table */}
          <Card sx={{ boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <HistoryIcon /> Historial de Ejecuciones
                </Typography>
                <Button size="small" onClick={loadExecutions} startIcon={<RefreshIcon />}>
                  Recargar
                </Button>
              </Box>

              {loadingExecutions ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                  <CircularProgress size={30} />
                </Box>
              ) : executions.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                  No se han registrado ejecuciones recientes.
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1.5 }}>
                  <Table size="small">
                    <TableHead sx={{ backgroundColor: '#f5f5f5' }}>
                      <TableRow>
                        <TableCell>ID</TableCell>
                        <TableCell>Fecha</TableCell>
                        <TableCell>Costo (Fitness)</TableCell>
                        <TableCell>Tiempo (s)</TableCell>
                        <TableCell>Estado</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {executions.map((exec) => (
                        <TableRow key={exec.id}>
                          <TableCell>{exec.id}</TableCell>
                          <TableCell>{new Date(exec.created_at).toLocaleDateString()}</TableCell>
                          <TableCell>{exec.funcion_objetivo?.toFixed(2) || '-'}</TableCell>
                          <TableCell>{exec.tiempo_ejecucion?.toFixed(1) || '-'}</TableCell>
                          <TableCell>
                            <Chip 
                              label={exec.estado} 
                              size="small" 
                              color={exec.estado === 'completed' ? 'success' : 'warning'}
                              variant="outlined"
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column: Files and Metrics */}
        <Grid item xs={12} md={5}>
          {/* Generated Files List */}
          <Card sx={{ mb: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Archivos Generados
                </Typography>
                <Button size="small" startIcon={<RefreshIcon />} onClick={loadFiles}>
                  Actualizar
                </Button>
              </Box>

              {files.length === 0 ? (
                <Alert severity="info">No hay archivos generados aún.</Alert>
              ) : (
                <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                  {files.map((file, index) => (
                    <React.Fragment key={file.filename}>
                      {index > 0 && <Divider />}
                      <ListItem sx={{ px: 1 }}>
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          {file.filename.endsWith('.json') ? (
                            <CodeIcon color="warning" />
                          ) : file.filename.endsWith('.csv') ? (
                            <TableViewIcon color="success" />
                          ) : (
                            <FileIcon color="primary" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" sx={{ fontWeight: 500, wordBreak: 'break-all' }}>
                              {file.filename}
                            </Typography>
                          }
                          secondary={new Date(file.created_at).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })}
                        />
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<DownloadIcon />}
                          onClick={() => downloadFile(file.filename)}
                          sx={{ textTransform: 'none' }}
                        >
                          Descargar
                        </Button>
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>

          {/* Standard Performance Metrics */}
          <Card sx={{ boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                <AssessmentIcon color="primary" /> Métricas de Producción
              </Typography>
              <Stack spacing={2}>
                <Paper variant="outlined" sx={{ p: 2, borderLeft: '4px solid #4caf50' }}>
                  <Typography variant="subtitle2" color="text.secondary">Cobertura Objetivo</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>100.0%</Typography>
                  <Typography variant="caption" color="success.main">Garantizado por Reparación Greedy</Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 2, borderLeft: '4px solid #1976d2' }}>
                  <Typography variant="subtitle2" color="text.secondary">Algoritmo</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>Híbrido v2</Typography>
                  <Typography variant="caption" color="text.secondary">ACO + GraphSAGE + Greedy Repair</Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 2, borderLeft: '4px solid #ff9800' }}>
                  <Typography variant="subtitle2" color="text.secondary">Capacidad de Procesamiento</Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>Soporta 298 secciones y 48 aulas simultáneamente.</Typography>
                </Paper>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
