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
  Stack
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Download as DownloadIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Description as FileIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export default function GenerarHorario() {
  const [status, setStatus] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);

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
            loadFiles(); // Reload file list
            
            // Auto-download if successful
            if (response.data.filename && !response.data.error) {
              downloadFile(response.data.filename);
            }
          }
        } catch (err) {
          console.error('Error checking status:', err);
        }
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [isGenerating]);

  // Load available files on mount
  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/horario/archivos`);
      setFiles(response.data.files || []);
    } catch (err) {
      console.error('Error loading files:', err);
    }
  };

  const startGeneration = async () => {
    setError(null);
    setIsGenerating(true);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/horario/generar`);
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
          Genera el horario completo usando el algoritmo híbrido ACO + GraphSAGE y descarga el archivo Excel con los horarios de todos los profesores.
        </Typography>
      </Box>

      {/* Generation Card */}
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
              La descarga debería iniciarse automáticamente.
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
                sx={{ height: 8, borderRadius: 1 }}
              />
            </Box>
          )}

          {/* Action Button */}
          <Button
            variant="contained"
            size="large"
            startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <PlayIcon />}
            onClick={startGeneration}
            disabled={isGenerating}
            fullWidth
            sx={{ 
              py: 1.5,
              fontSize: '1.1rem',
              fontWeight: 600
            }}
          >
            {isGenerating ? 'Generando Horario...' : 'Generar Horario Completo'}
          </Button>

          {/* Info */}
          <Box sx={{ mt: 2, p: 2, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Proceso de generación:</strong>
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText 
                  primary="1. Construye el grafo heterogéneo de restricciones"
                  secondary="Representa secciones, profesores, aulas, franjas horarias y sus relaciones"
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="2. Ejecuta GraphSAGE para generar embeddings"
                  secondary="La red neuronal aprende patrones complejos del horario actual"
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="3. Ejecuta ACO guiado por heurísticas neuronales"
                  secondary="40 hormigas exploran soluciones durante hasta 150 iteraciones"
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="4. Exporta los resultados a Excel"
                  secondary="Crea un archivo con horarios individuales para cada profesor (16 bloques de 50 min)"
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="5. Descarga automática"
                  secondary="El archivo Excel se descarga automáticamente al completarse"
                />
              </ListItem>
            </List>
            <Alert severity="info" sx={{ mt: 1 }}>
              ⏱️ <strong>Tiempo estimado:</strong> 5-10 minutos
              <br />
              🧠 <strong>Algoritmo:</strong> ACO + GraphSAGE (Híbrido)
              <br />
              
            </Alert>
          </Box>
        </CardContent>
      </Card>

      {/* Files History */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Horarios Generados
            </Typography>
            <Button
              size="small"
              startIcon={<RefreshIcon />}
              onClick={loadFiles}
            >
              Actualizar
            </Button>
          </Box>

          {files.length === 0 ? (
            <Alert severity="info">
              No hay archivos generados aún. Genera tu primer horario usando el botón de arriba.
            </Alert>
          ) : (
            <List>
              {files.map((file, index) => (
                <React.Fragment key={file.filename}>
                  {index > 0 && <Divider />}
                  <ListItem
                    sx={{ 
                      '&:hover': { backgroundColor: '#f5f5f5' },
                      borderRadius: 1
                    }}
                  >
                    <ListItemIcon>
                      <FileIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body1" sx={{ fontWeight: 500 }}>
                            {file.filename}
                          </Typography>
                          <Chip 
                            label={`${file.size_mb} MB`} 
                            size="small" 
                            color="default"
                          />
                        </Box>
                      }
                      secondary={
                        <Typography variant="body2" color="text.secondary">
                          Creado: {new Date(file.created_at).toLocaleString('es-PE')}
                        </Typography>
                      }
                    />
                    <Button
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
    </Box>
  );
}
