import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authstore'
import Navbar         from './components/navbar'
import CheckInOut     from './pages/checkinout'
import AdminLogin     from './pages/adminlogin'
import AdminDashboard from './pages/admindashboard'
import RegisterEmployee from './pages/registeremployee'
import AttendanceLogs   from './pages/attendancelog'

function PrivateRoute({ children }) {
  const token = useAuthStore(s => s.token)
  return token ? children : <Navigate to="/admin/login" replace />
}

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/"                  element={<CheckInOut />} />
        <Route path="/admin/login"       element={<AdminLogin />} />
        <Route path="/admin/dashboard"   element={<PrivateRoute><AdminDashboard /></PrivateRoute>} />
        <Route path="/admin/register"    element={<PrivateRoute><RegisterEmployee /></PrivateRoute>} />
        <Route path="/admin/logs"        element={<PrivateRoute><AttendanceLogs /></PrivateRoute>} />
      </Routes>
    </>
  )
}
