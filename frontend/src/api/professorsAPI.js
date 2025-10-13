import axios from 'axios';

const API_BASE = 'http://localhost:8001';

export const professorsAPI = {
  // Obtener todos los profesores
  getProfessors: async () => {
    const response = await axios.get(`${API_BASE}/api/professors`);
    return response.data;
  },

  // Crear profesor
  createProfessor: async (data) => {
    const response = await axios.post(`${API_BASE}/api/professors`, data);
    return response.data;
  },

  // Actualizar profesor
  updateProfessor: async (profId, data) => {
    const response = await axios.put(`${API_BASE}/api/professors/${profId}`, data);
    return response.data;
  },

  // Eliminar profesor
  deleteProfessor: async (profId) => {
    const response = await axios.delete(`${API_BASE}/api/professors/${profId}`);
    return response.data;
  },
};
