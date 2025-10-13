import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Projections from './pages/Projections';
import Professors from './pages/Professors';
import ProfessorsUpload from './pages/ProfessorsUpload';
import Courses from './pages/Courses';
import ProfessorRestrictions from './pages/ProfessorRestrictions';
import Classrooms from './pages/Classrooms';
import ProfessorAssignments from './pages/ProfessorAssignments';

function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user } = useAuth();

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <Header user={user} onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        
        <Box component="main" sx={{ flexGrow: 1, p: 3, backgroundColor: '#f5f5f5' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/projections" element={<Projections />} />
            <Route path="/professors" element={<Professors />} />
            <Route path="/professor-assignments" element={<ProfessorAssignments />} />
            <Route path="/professors-upload" element={<ProfessorsUpload />} />
            <Route path="/courses" element={<Courses />} />
            <Route path="/restrictions" element={<ProfessorRestrictions />} />
            <Route path="/classrooms" element={<Classrooms />} />
          </Routes>
        </Box>
      </Box>
    </Box>
  );
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
