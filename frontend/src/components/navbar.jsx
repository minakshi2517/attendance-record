import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authstore'

export default function Navbar() {
  const { token, adminName, logout } = useAuthStore()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)

  const handleLogout = () => { logout(); nav('/'); setOpen(false) }

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-logo" onClick={() => setOpen(false)}>Attendance</Link>

        <button className="navbar-toggle" onClick={() => setOpen(o => !o)} aria-label="Menu">
          {open ? '✕' : '☰'}
        </button>

        <div className={`navbar-links ${open ? 'open' : ''}`}>
          <Link to="/" className="nav-link" onClick={() => setOpen(false)}>Check In / Out</Link>
          {token ? (
            <>
              <Link to="/admin/dashboard" className="nav-link" onClick={() => setOpen(false)}>Dashboard</Link>
              <Link to="/admin/register"  className="nav-link" onClick={() => setOpen(false)}>Register</Link>
              <Link to="/admin/logs"      className="nav-link" onClick={() => setOpen(false)}>Logs</Link>
              <span className="nav-user">Hi, {adminName}</span>
              <button className="nav-logout" onClick={handleLogout}>Logout</button>
            </>
          ) : (
            <Link to="/admin/login" className="nav-link" onClick={() => setOpen(false)}>Admin Login</Link>
          )}
        </div>
      </div>
    </nav>
  )
}
