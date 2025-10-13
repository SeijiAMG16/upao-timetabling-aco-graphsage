import axios from 'axios';

const API_BASE = 'http://localhost:8001';

export const projectionsAPI = {
  // Upload Excel
  uploadExcel: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${API_BASE}/api/projections/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  // Confirmar proyecciones
  confirmProjections: async (courses) => {
    const response = await axios.post(`${API_BASE}/api/projections/confirm`, { courses });
    return response.data;
  },

  // Obtener todos los cursos
  getCourses: async () => {
    const response = await axios.get(`${API_BASE}/api/projections/courses`);
    return response.data;
  },

  // Actualizar curso
  updateCourse: async (courseId, data) => {
    const response = await axios.put(`${API_BASE}/api/projections/courses/${courseId}`, data);
    return response.data;
  },

  // Crear curso
  createCourse: async (data) => {
    const response = await axios.post(`${API_BASE}/api/projections/courses`, data);
    return response.data;
  },

  // Eliminar curso
  deleteCourse: async (courseId) => {
    const response = await axios.delete(`${API_BASE}/api/projections/courses/${courseId}`);
    return response.data;
  },
};
