import React, { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

const s = {
  page:  { maxWidth:980, margin:'40px auto', padding:24 },
  title: { fontSize:26, fontWeight:700, color:'#818cf8', marginBottom:24 },
  toolbar: { display:'flex', gap:12, flexWrap:'wrap', marginBottom:24 },
  cards: { display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(180px,1fr))', gap:16, marginBottom:32 },
  card:  { background:'#1e293b', borderRadius:12, padding:20, textAlign:'center', border:'2px solid transparent' },
  cardClickable: { cursor:'pointer', border:'2px solid #6366f1' },
  num:   { fontSize:36, fontWeight:700, color:'#10b981', marginBottom:4 },
  label: { color:'#64748b', fontSize:14 },
  table: { width:'100%', borderCollapse:'collapse', marginTop:16 },
  th:    { background:'#1e293b', padding:'10px 14px', textAlign:'left', color:'#94a3b8', fontSize:13 },
  td:    { padding:'10px 14px', borderBottom:'1px solid #1e293b', fontSize:14 },
  row:   { cursor:'pointer' },
  badge: (active) => ({
    padding:'3px 10px', borderRadius:20, fontSize:12, fontWeight:600,
    background: active ? '#064e3b' : '#450a0a',
    color: active ? '#10b981' : '#ef4444',
  }),
  statusBadge: (inOffice) => ({
    padding:'3px 10px', borderRadius:20, fontSize:12, fontWeight:600,
    background: inOffice ? '#064e3b' : '#1e293b',
    color: inOffice ? '#10b981' : '#94a3b8',
  }),
  addBtn:{ background:'#6366f1', color:'#fff' },
  secBtn:{ background:'#334155', color:'#fff' },
  section:{ color:'#94a3b8', marginBottom:12, fontSize:18, marginTop:32 },
  err:   { background:'#450a0a', color:'#ef4444', padding:12, borderRadius:8, marginBottom:16 },
  ok:    { background:'#064e3b', color:'#10b981', padding:12, borderRadius:8, marginBottom:16 },
  modal: { position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:100, padding:16 },
  modalBox: { background:'#1e293b', borderRadius:16, padding:28, maxWidth:440, width:'100%' },
  detailRow: { display:'flex', justifyContent:'space-between', padding:'10px 0', borderBottom:'1px solid #334155', color:'#e2e8f0' },
  detailLabel: { color:'#94a3b8' },
  field: { marginBottom:14 },
  fieldLabel: { display:'block', color:'#94a3b8', fontSize:13, marginBottom:6 },
}

export default function AdminDashboard() {
  const [stats, setStats]         = useState(null)
  const [logs,  setLogs]          = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading]     = useState(true)
  const [err, setErr]             = useState('')
  const [notice, setNotice]       = useState('')
  const [selected, setSelected]   = useState(null)   // employee shown in details modal
  const [editing, setEditing]     = useState(null)   // employee being edited
  const [editForm, setEditForm]   = useState({ name:'', employee_id:'', department:'' })
  const [saving, setSaving]       = useState(false)
  const teamRef = useRef(null)

  const flash = (msg) => { setNotice(msg); setTimeout(() => setNotice(''), 3000) }

  const loadData = async () => {
    setLoading(true); setErr('')
    try {
      const [statsRes, logsRes, empRes] = await Promise.all([
        api.get('/api/attendance/stats'),
        api.get('/api/attendance/today'),
        api.get('/api/employees/'),
      ])
      setStats(statsRes.data)
      setLogs(logsRes.data)
      setEmployees(empRes.data)
    } catch (e) {
      setErr(e.response?.status === 401
        ? 'Your session has expired. Please log in again.'
        : 'Could not load data. Make sure the backend server is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const scrollToTeam = () => teamRef.current?.scrollIntoView({ behavior:'smooth' })

  const handleDelete = async (employeeId, name) => {
    if (!window.confirm(`Delete ${name}? This cannot be undone.`)) return
    try {
      await api.delete(`/api/employees/${employeeId}`)
      setEmployees(prev => prev.filter(e => e.employee_id !== employeeId))
      setSelected(null)
      flash(`${name} deleted.`)
      const statsRes = await api.get('/api/attendance/stats')
      setStats(statsRes.data)
    } catch (e) {
      alert(e.response?.data?.detail || 'Delete failed.')
    }
  }

  const toggleActive = async (emp) => {
    const action = emp.is_active ? 'deactivate' : 'activate'
    try {
      await api.patch(`/api/employees/${emp.employee_id}/${action}`)
      const updated = { ...emp, is_active: !emp.is_active }
      setEmployees(prev => prev.map(e => e.employee_id === emp.employee_id ? updated : e))
      setSelected(prev => prev && prev.employee_id === emp.employee_id ? updated : prev)
      flash(`${emp.name} ${emp.is_active ? 'deactivated' : 'activated'}.`)
      const statsRes = await api.get('/api/attendance/stats')
      setStats(statsRes.data)
    } catch (e) {
      alert(e.response?.data?.detail || 'Status update failed.')
    }
  }

  const openEdit = (emp) => {
    setSelected(null)
    setEditing(emp)
    setEditForm({ name: emp.name, employee_id: emp.employee_id, department: emp.department || '' })
  }

  const saveEdit = async () => {
    if (!editForm.name.trim() || !editForm.employee_id.trim()) {
      alert('Name and Employee ID are required.')
      return
    }
    setSaving(true)
    try {
      const { data } = await api.patch(`/api/employees/${editing.employee_id}`, {
        name: editForm.name.trim(),
        employee_id: editForm.employee_id.trim(),
        department: editForm.department.trim(),
      })
      setEmployees(prev => prev.map(e =>
        e.employee_id === editing.employee_id
          ? { ...e, name: data.name, employee_id: data.employee_id, department: data.department }
          : e
      ))
      flash('Employee updated.')
      setEditing(null)
    } catch (e) {
      alert(e.response?.data?.detail || 'Update failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>Admin Dashboard</h1>

      <div style={s.toolbar}>
        <Link to="/admin/register"><button style={s.addBtn}>+ Register Employee</button></Link>
        <Link to="/admin/logs"><button style={s.secBtn}>View Full Logs</button></Link>
        <button style={s.secBtn} onClick={loadData} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {err && <div style={s.err}>{err}</div>}
      {notice && <div style={s.ok}>{notice}</div>}

      {stats && (
        <div style={s.cards}>
          <div style={{...s.card, ...s.cardClickable}} onClick={scrollToTeam} title="View team list">
            <div style={{...s.num, color:'#818cf8'}}>{stats.total_active_employees}</div>
            <div style={s.label}>Total Employees</div>
            <div style={{color:'#6366f1', fontSize:12, marginTop:6}}>Click to view list</div>
          </div>
          <div style={s.card}>
            <div style={{...s.num, color:'#10b981'}}>{stats.checked_in_today}</div>
            <div style={s.label}>Checked In Today</div>
          </div>
          <div style={s.card}>
            <div style={{...s.num, color:'#f59e0b'}}>{stats.currently_in_office}</div>
            <div style={s.label}>Currently In Office</div>
          </div>
          <div style={s.card}>
            <div style={{...s.num, color:'#ef4444'}}>{stats.absent_today}</div>
            <div style={s.label}>Absent Today</div>
          </div>
        </div>
      )}

      <h2 style={s.section} ref={teamRef}>Registered Team Members ({employees.length})</h2>
      <p style={{color:'#64748b', fontSize:13, marginBottom:8}}>Click any row to view full details, edit, or delete.</p>
      <table style={s.table}>
        <thead>
          <tr>{['Name','Employee ID','Department','Registered','Status','Actions'].map(h =>
            <th key={h} style={s.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {employees.map((emp, i) => (
            <tr
              key={emp.id}
              style={{...s.row, background: i%2===0 ? '#0f172a' : 'transparent'}}
              onClick={() => setSelected(emp)}
            >
              <td style={s.td}>{emp.name}</td>
              <td style={s.td}>{emp.employee_id}</td>
              <td style={s.td}>{emp.department || '-'}</td>
              <td style={s.td}>{emp.registered_at ? new Date(emp.registered_at).toLocaleDateString('en-GB') : '-'}</td>
              <td style={s.td}><span style={s.badge(emp.is_active)}>{emp.is_active ? 'Active' : 'Inactive'}</span></td>
              <td style={s.td} onClick={e => e.stopPropagation()}>
                <div style={{display:'flex', gap:8}}>
                  <button style={{background:'#6366f1', color:'#fff', padding:'4px 12px', fontSize:12}}
                    onClick={() => openEdit(emp)}>Edit</button>
                  <button style={{background:'#ef4444', color:'#fff', padding:'4px 12px', fontSize:12}}
                    onClick={() => handleDelete(emp.employee_id, emp.name)}>Delete</button>
                </div>
              </td>
            </tr>
          ))}
          {!loading && employees.length === 0 && (
            <tr><td colSpan={6} style={{...s.td, textAlign:'center', color:'#64748b'}}>
              No employees registered yet. Click "+ Register Employee" above to add one.
            </td></tr>
          )}
        </tbody>
      </table>

      <h2 style={s.section}>Today's Attendance</h2>
      <table style={s.table}>
        <thead>
          <tr>{['Name','ID','Department','Check In','Check Out','Duration','Status'].map(h =>
            <th key={h} style={s.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {logs.map((log, i) => (
            <tr key={i} style={{background: i%2===0 ? '#0f172a' : 'transparent'}}>
              <td style={s.td}>{log.employee_name}</td>
              <td style={s.td}>{log.employee_id}</td>
              <td style={s.td}>{log.department || '-'}</td>
              <td style={s.td}>{log.check_in  ? new Date(log.check_in ).toLocaleTimeString('en-GB') : '-'}</td>
              <td style={s.td}>{log.check_out ? new Date(log.check_out).toLocaleTimeString('en-GB') : '-'}</td>
              <td style={s.td}>{log.duration || '-'}</td>
              <td style={s.td}><span style={s.statusBadge(!log.check_out)}>{log.check_out ? 'Completed' : 'In Office'}</span></td>
            </tr>
          ))}
          {logs.length === 0 && <tr><td colSpan={7} style={{...s.td, textAlign:'center', color:'#64748b'}}>No attendance recorded today yet.</td></tr>}
        </tbody>
      </table>

      {selected && (
        <div style={s.modal} onClick={() => setSelected(null)}>
          <div style={s.modalBox} onClick={e => e.stopPropagation()}>
            <h3 style={{color:'#818cf8', marginBottom:16}}>{selected.name}</h3>
            {[
              ['Employee ID', selected.employee_id],
              ['Department',  selected.department || 'N/A'],
              ['Status',      selected.is_active ? 'Active' : 'Inactive'],
              ['Registered',  selected.registered_at ? new Date(selected.registered_at).toLocaleString('en-GB') : '-'],
            ].map(([label, val]) => (
              <div key={label} style={s.detailRow}>
                <span style={s.detailLabel}>{label}</span>
                <span>{val}</span>
              </div>
            ))}
            <div style={{display:'flex', gap:10, marginTop:20}}>
              <button style={{background:'#6366f1', color:'#fff', flex:1}} onClick={() => openEdit(selected)}>Edit</button>
              <button style={{background:'#f59e0b', color:'#fff', flex:1}} onClick={() => toggleActive(selected)}>
                {selected.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button style={{background:'#ef4444', color:'#fff', flex:1}} onClick={() => handleDelete(selected.employee_id, selected.name)}>Delete</button>
            </div>
            <button style={{background:'#334155', color:'#fff', width:'100%', marginTop:10}} onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}

      {editing && (
        <div style={s.modal} onClick={() => !saving && setEditing(null)}>
          <div style={s.modalBox} onClick={e => e.stopPropagation()}>
            <h3 style={{color:'#818cf8', marginBottom:20}}>Edit Employee</h3>
            <div style={s.field}>
              <label style={s.fieldLabel}>Full Name</label>
              <input value={editForm.name} onChange={e => setEditForm({...editForm, name:e.target.value})} />
            </div>
            <div style={s.field}>
              <label style={s.fieldLabel}>Employee ID</label>
              <input value={editForm.employee_id} onChange={e => setEditForm({...editForm, employee_id:e.target.value})} />
            </div>
            <div style={s.field}>
              <label style={s.fieldLabel}>Department</label>
              <input value={editForm.department} onChange={e => setEditForm({...editForm, department:e.target.value})} />
            </div>
            <div style={{display:'flex', gap:10, marginTop:8}}>
              <button style={{background:'#10b981', color:'#fff', flex:1}} onClick={saveEdit} disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button style={{background:'#334155', color:'#fff', flex:1}} onClick={() => setEditing(null)} disabled={saving}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
