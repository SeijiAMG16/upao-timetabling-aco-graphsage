import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const classroomsAPI = {
  // Obtener todas las aulas
  getClassrooms: async () => {
    const response = await axios.get(`${API_BASE}/api/classrooms`);
    return response.data;
  },

  // Crear aula
  createClassroom: async (data) => {
    const response = await axios.post(`${API_BASE}/api/classrooms`, data);
    return response.data;
  },

  // Actualizar aula
  updateClassroom: async (classroomId, data) => {
    const response = await axios.put(`${API_BASE}/api/classrooms/${classroomId}`, data);
    return response.data;
  },

  // Eliminar aula
  deleteClassroom: async (classroomId) => {
    const response = await axios.delete(`${API_BASE}/api/classrooms/${classroomId}`);
    return response.data;
  },
};
