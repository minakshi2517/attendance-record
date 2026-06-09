import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

const s = {
  page:  { maxWidth:900, margin:'40px auto', padding:24 },
  title: { fontSize:26, fontWeight:700, color:'#818cf8', marginBottom:24 },
  cards: { display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(180px,1fr))', gap:16, marginBottom:32 },
  card:  { background:'#1e293b', borderRadius:12, padding:20, textAlign:'center' },
  num:   { fontSize:36, fontWeight:700, color:'#10b981', marginBottom:4 },
  label: { color:'#64748b', fontSize:14 },
  table: { width:'100%', borderCollapse:'collapse', marginTop:16 },
  th:    { background:'#1e293b', padding:'10px 14px', textAlign:'left', color:'#94a3b8', fontSize:13 },
  td:    { padding:'10px 14px', borderBottom:'1px solid #1e293b', fontSize:14 },
  badge: (s) => ({ padding:'3px 10px', borderRadius:20, fontSize:12, fontWeight:600,
    background: s==='Office mein hai' ? '#064e3b' : '#1e293b',
    color: s==='Office mein hai' ? '#10b981' : '#94a3b8' }),
  addBtn:{ background:'#6366f1', color:'#fff', marginBottom:20 },
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [logs,  setLogs]  = useState([])

  useEffect(() => {
    api.get('/api/attendance/stats').then(r => setStats(r.data))
    api.get('/api/attendance/today').then(r => setLogs(r.data))
  }, [])

  return (
    <div style={s.page}>
      <h1 style={s.title}>Admin Dashboard</h1>
      <Link to="/admin/register"><button style={s.addBtn}>+ Employee Register Karo</button></Link>
      <Link to="/admin/logs"    style={{marginLeft:12}}><button style={{background:'#334155',color:'#fff'}}>📋 Full Logs</button></Link>

      {/* Stats Cards */}
      {stats && (
        <div style={s.cards}>
          {[
            ['Total Employees', stats.total_active_employees, '#818cf8'],
            ['Aaj Check-in',    stats.checked_in_today,       '#10b981'],
            ['Abhi Office Mein',stats.currently_in_office,    '#f59e0b'],
            ['Absent Aaj',      stats.absent_today,           '#ef4444'],
          ].map(([label, num, color]) => (
            <div key={label} style={s.card}>
              <div style={{...s.num, color}}>{num}</div>
              <div style={s.label}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Today's Attendance Table */}
      <h2 style={{color:'#94a3b8', marginBottom:12, fontSize:18}}>Aaj ki Attendance</h2>
      <table style={s.table}>
        <thead>
          <tr>{['Naam','ID','Department','Check In','Check Out','Duration','Status'].map(h =>
            <th key={h} style={s.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {logs.map((log, i) => (
            <tr key={i} style={{background: i%2===0 ? '#0f172a' : 'transparent'}}>
              <td style={s.td}>{log.employee_name}</td>
              <td style={s.td}>{log.employee_id}</td>
              <td style={s.td}>{log.department || '-'}</td>
              <td style={s.td}>{log.check_in  ? new Date(log.check_in ).toLocaleTimeString('hi-IN') : '-'}</td>
              <td style={s.td}>{log.check_out ? new Date(log.check_out).toLocaleTimeString('hi-IN') : '-'}</td>
              <td style={s.td}>{log.duration || '-'}</td>
              <td style={s.td}><span style={s.badge(log.status)}>{log.status}</span></td>
            </tr>
          ))}
          {logs.length === 0 && <tr><td colSpan={7} style={{...s.td, textAlign:'center', color:'#64748b'}}>Aaj koi nahi aaya abhi tak</td></tr>}
        </tbody>
      </table>
    </div>
  )
}