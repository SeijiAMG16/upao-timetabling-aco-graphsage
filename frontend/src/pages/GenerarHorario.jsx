import React, { useState, useEffect } from 'react';
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
  Grid
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Download as DownloadIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Description as FileIcon,
  Refresh as RefreshIcon,
  History as HistoryIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function GenerarHorario() {
  const [status, setStatus] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [files, setFiles] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [error, setError] = useState(null);
  const [loadingExecutions, setLoadingExecutions] = useState(false);

  // Poll status when generating
  useEffect(() => {
    if (isGenerating) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/api/horario/status`);
          setStatus(response.data);
          
          // Stop polling if generation completed or failed
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
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [isGenerating]);

  // Load available files and executions on mount
  useEffect(() => {
    loadFiles();
    loadExecutions();
  }, []);

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
    
    try {
      await axios.post(`${API_BASE_URL}/api/horario/generar`);
      setStatus({
        is_running: true,
        progress: 0,
        message: 'Iniciando generación...',
        started_at: new Date().toISOString()
      });
    } catch (err) {
      setError(err.response?.data?.error || 'Error al iniciar la generación');
      setIsGenerating(false);
    }
  };

  const downloadFile = (filename) => {
    const url = `${API_BASE_URL}/api/horario/descargar/${filename}`;
    window.open(url, '_blank');
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScheduleIcon sx={{ fontSize: 36 }} />
          Generar Horario
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Genera el horario completo usando el algoritmo híbrido <strong>ACO + GraphSAGE con Reparación Greedy</strong> y descarga el archivo Excel con los horarios.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Left Column: Actions and Progress */}
        <Grid item xs={12} md={7}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Nueva Generación
              </Typography>
              
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <AlertTitle>Error</AlertTitle>
                  {error}
                </Alert>
              )}

              {status && status.error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <AlertTitle>Error en la Generación</AlertTitle>
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

              {/* Progress */}
              {isGenerating && (
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {status?.message || 'Procesando...'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {status?.progress || 0}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={status?.progress || 0}
                    sx={{ height: 10, borderRadius: 1 }}
                  />
                </Box>
              )}

              <Button
                variant="contained"
                size="large"
                startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <PlayIcon />}
                onClick={startGeneration}
                disabled={isGenerating}
                fullWidth
                sx={{ py: 1.5, fontSize: '1.1rem', fontWeight: 600 }}
              >
                {isGenerating ? 'Generando Horario...' : 'Generar Horario Completo (ACO + GraphSAGE)'}
              </Button>

              <Box sx={{ mt: 3, p: 2, backgroundColor: '#f8faff', borderRadius: 2, border: '1px solid #e3f2fd' }}>
                <Typography variant="subtitle2" sx={{ color: '#1976d2', fontWeight: 600, mb: 1 }}>
                  Detalles del Algoritmo Híbrido:
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="1. Representación en Grafo Heterogéneo"
                      secondary="Mapea todas las restricciones y relaciones complejas entre recursos."
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="2. Heurística Neural GraphSAGE"
                      secondary="Inyecta inteligencia predictiva en la selección de las hormigas."
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="3. Optimización ACO (Ant Colony)"
                      secondary="Exploración masiva de soluciones factibles buscando el costo mínimo."
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="4. Fase de Reparación Greedy"
                      secondary="Nueva fase que fuerza la asignación del 100% de secciones faltantes."
                    />
                  </ListItem>
                </List>
              </Box>
            </CardContent>
          </Card>

          {/* Execution History Table */}
          <Card>
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
                <TableContainer component={Paper} variant="outlined">
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
          <Card sx={{ mb: 3 }}>
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
                          <FileIcon color="primary" />
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

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                <AssessmentIcon /> Métricas de Producción
              </Typography>
              <Stack spacing={2}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Cobertura Objetivo</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>100.0%</Typography>
                  <Typography variant="caption" color="success.main">Garantizado por Reparación Greedy</Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Algoritmo</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>Híbrido v2</Typography>
                  <Typography variant="caption" color="text.secondary">ACO + GraphSAGE + Greedy Repair</Typography>
                </Paper>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Capacidad de Procesamiento</Typography>
                  <Typography variant="body2">Soporta 298 secciones y 48 aulas simultáneamente.</Typography>
                </Paper>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
