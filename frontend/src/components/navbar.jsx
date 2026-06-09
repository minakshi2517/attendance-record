import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authstore'

const s = {
  nav:  { background:'#1e293b', padding:'14px 24px', display:'flex', justifyContent:'space-between', alignItems:'center' },
  logo: { fontSize:20, fontWeight:700, color:'#818cf8', textDecoration:'none' },
  links:{ display:'flex', gap:20 },
  link: { color:'#94a3b8', textDecoration:'none', fontSize:14 },
  btn:  { background:'#ef4444', color:'#fff', padding:'6px 16px', fontSize:13 },
}

export default function Navbar() {
  const { token, adminName, logout } = useAuthStore()
  const nav = useNavigate()

  const handleLogout = () => { logout(); nav('/') }

  return (
    <nav style={s.nav}>
      <Link to="/" style={s.logo}>🎯 Attendance</Link>
      <div style={s.links}>
        <Link to="/"             style={s.link}>Check In/Out</Link>
        {token ? (
          <>
            <Link to="/admin/dashboard" style={s.link}>Dashboard</Link>
            <Link to="/admin/register"  style={s.link}>Register</Link>
            <Link to="/admin/logs"      style={s.link}>Logs</Link>
            <span style={{color:'#64748b', fontSize:13}}>Hi, {adminName}</span>
            <button style={s.btn} onClick={handleLogout}>Logout</button>
          </>
        ) : (
          <Link to="/admin/login" style={s.link}>Admin Login</Link>
        )}
      </div>
    </nav>
  )
}
