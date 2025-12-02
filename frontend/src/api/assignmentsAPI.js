import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const assignmentsAPI = {
  getCoursesWithAssignments: async () => {
    const response = await axios.get(`${API_BASE}/api/assignments/courses-with-assignments`);
    return response.data;
  },

  updateCourseAssignments: async (courseId, payload) => {
    const response = await axios.put(
      `${API_BASE}/api/assignments/professor-courses/course/${courseId}`,
      payload
    );
    return response.data;
  }
};
