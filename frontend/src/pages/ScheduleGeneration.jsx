import React from 'react';
import { Alert, Box, Button, Card, CardContent, Divider, Stack, Typography } from '@mui/material';
import ScienceIcon from '@mui/icons-material/Science';
import TimelineIcon from '@mui/icons-material/Timeline';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';

const ScheduleGeneration = () => {
	return (
		<Box sx={{ px: 1 }}>
			<Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
				<Box>
					<Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
						<TimelineIcon />
						Generación de Horarios
					</Typography>
					<Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
						Ejecuta pruebas con los motores ACO y GraphSAGE y visualiza los resultados cuando estén
						disponibles.
					</Typography>
				</Box>
			</Box>

			<Stack spacing={2} direction={{ xs: 'column', md: 'row' }}>
				<Card sx={{ flex: 1 }}>
					<CardContent>
						<Stack direction="row" spacing={1} alignItems="center" mb={2}>
							<ScienceIcon color="primary" />
							<Typography variant="h6">Simulación ACO</Typography>
						</Stack>
						<Typography variant="body2" color="text.secondary" mb={2}>
							Configura parámetros y ejecuta el algoritmo de colonia de hormigas para generar horarios
							experimentales.
						</Typography>
						<Button variant="contained" startIcon={<PlayArrowIcon />} disabled>
							Próximamente
						</Button>
					</CardContent>
				</Card>

				<Card sx={{ flex: 1 }}>
					<CardContent>
						<Stack direction="row" spacing={1} alignItems="center" mb={2}>
							<TimelineIcon color="primary" />
							<Typography variant="h6">Predicción GraphSAGE</Typography>
						</Stack>
						<Typography variant="body2" color="text.secondary" mb={2}>
							Corre el modelo GraphSAGE para sugerir asignaciones óptimas basadas en historiales y
							restricciones.
						</Typography>
						<Button variant="contained" startIcon={<PlayArrowIcon />} disabled>
							Próximamente
						</Button>
					</CardContent>
				</Card>
			</Stack>

			<Divider sx={{ my: 3 }} />

			<Alert severity="info">
				Integraremos los reportes de ejecución y la visualización de horarios en esta sección una vez que
				los scripts estén disponibles vía API. Mientras tanto, utiliza la asignación manual de profesores y las
				restricciones para preparar la data base.
			</Alert>
		</Box>
	);
};

export default ScheduleGeneration;
