import React, { useState, useEffect } from 'react'
import api from '../api'

const s = {
  page:    { maxWidth:1000, margin:'40px auto', padding:24 },
  title:   { fontSize:22, fontWeight:700, color:'#818cf8', marginBottom:20 },
  filters: { display:'flex', gap:12, flexWrap:'wrap', marginBottom:20 },
  inp:     { width:'auto', flex:1, minWidth:160, marginBottom:0 },
  btn:     { background:'#6366f1', color:'#fff', padding:'10px 20px' },
  table:   { width:'100%', borderCollapse:'collapse' },
  th:      { background:'#1e293b', padding:'10px 14px', textAlign:'left', color:'#94a3b8', fontSize:13 },
  td:      { padding:'10px 14px', borderBottom:'1px solid #1e293b', fontSize:13 },
}

export default function AttendanceLogs() {
  const [logs,   setLogs]   = useState([])
  const [empId,  setEmpId]  = useState('')
  const [from,   setFrom]   = useState('')
  const [to,     setTo]     = useState('')

  const fetchLogs = async () => {
    const params = {}
    if (empId) params.employee_id = empId
    if (from)  params.date_from   = from
    if (to)    params.date_to     = to
    const { data } = await api.get('/api/attendance/history', { params })
    setLogs(data)
  }

  useEffect(() => { fetchLogs() }, [])

  return (
    <div style={s.page}>
      <h1 style={s.title}>📋 Attendance Logs</h1>
      <div style={s.filters}>
        <input style={s.inp} placeholder="Employee ID filter karo" value={empId} onChange={e => setEmpId(e.target.value)} />
        <input style={s.inp} type="date" value={from} onChange={e => setFrom(e.target.value)} />
        <input style={s.inp} type="date" value={to}   onChange={e => setTo(e.target.value)} />
        <button style={s.btn} onClick={fetchLogs}>🔍 Search</button>
        <button style={{...s.btn, background:'#334155'}} onClick={() => { setEmpId(''); setFrom(''); setTo(''); fetchLogs() }}>Reset</button>
      </div>
      <p style={{color:'#64748b', marginBottom:12, fontSize:13}}>Total records: {logs.length}</p>
      <table style={s.table}>
        <thead>
          <tr>{['Naam','Employee ID','Department','Check In','Check Out','Duration','Status'].map(h =>
            <th key={h} style={s.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {logs.map((log, i) => (
            <tr key={i} style={{background: i%2===0 ? '#0f172a' : 'transparent'}}>
              <td style={s.td}>{log.employee_name}</td>
              <td style={s.td}>{log.employee_id}</td>
              <td style={s.td}>{log.department || '-'}</td>
              <td style={s.td}>{log.check_in  ? new Date(log.check_in ).toLocaleString('hi-IN') : '-'}</td>
              <td style={s.td}>{log.check_out ? new Date(log.check_out).toLocaleString('hi-IN') : '-'}</td>
              <td style={s.td}>{log.duration || '—'}</td>
              <td style={s.td}>
                <span style={{padding:'3px 8px', borderRadius:20, fontSize:11, fontWeight:600,
                  background: log.check_out ? '#1e293b' : '#064e3b',
                  color:      log.check_out ? '#94a3b8'  : '#10b981'}}>
                  {log.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}