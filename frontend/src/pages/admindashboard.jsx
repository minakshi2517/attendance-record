import React, { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

export default function AdminDashboard() {
  const [stats, setStats]         = useState(null)
  const [logs,  setLogs]          = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading]     = useState(true)
  const [err, setErr]             = useState('')
  const [notice, setNotice]       = useState('')
  const [selected, setSelected]   = useState(null)
  const [editing, setEditing]     = useState(null)
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
        ? 'Session expired. Please log in again.'
        : 'Could not load data. Check that the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

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
      alert('Name and Employee ID are required.'); return
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

  const EmpCard = ({ emp }) => (
    <div className="emp-card" onClick={() => setSelected(emp)}>
      <div className="emp-card-name">{emp.name}</div>
      <div className="emp-card-meta">
        ID: {emp.employee_id} · {emp.department || 'No dept'} ·{' '}
        <span className={`badge ${emp.is_active ? 'badge-green' : 'badge-red'}`}>
          {emp.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>
      <div className="emp-card-actions" onClick={e => e.stopPropagation()}>
        <button className="btn-primary btn-sm" onClick={() => openEdit(emp)}>Edit</button>
        <button className="btn-danger btn-sm" onClick={() => handleDelete(emp.employee_id, emp.name)}>Delete</button>
      </div>
    </div>
  )

  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>

      <div className="toolbar">
        <Link to="/admin/register"><button className="btn-primary">+ Register</button></Link>
        <Link to="/admin/logs"><button className="btn-secondary">Logs</button></Link>
        <button className="btn-secondary" onClick={loadData} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {err && <div className="alert alert-error">{err}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {stats && (
        <div className="stat-grid">
          <div className="stat-card" onClick={() => teamRef.current?.scrollIntoView({behavior:'smooth'})} style={{cursor:'pointer'}}>
            <div className="stat-num" style={{color:'#818cf8'}}>{stats.total_active_employees}</div>
            <div className="stat-label">Employees</div>
          </div>
          <div className="stat-card">
            <div className="stat-num" style={{color:'#10b981'}}>{stats.checked_in_today}</div>
            <div className="stat-label">Checked In</div>
          </div>
          <div className="stat-card">
            <div className="stat-num" style={{color:'#f59e0b'}}>{stats.currently_in_office}</div>
            <div className="stat-label">In Office</div>
          </div>
          <div className="stat-card">
            <div className="stat-num" style={{color:'#ef4444'}}>{stats.absent_today}</div>
            <div className="stat-label">Absent</div>
          </div>
        </div>
      )}

      <h2 className="section-title" ref={teamRef}>Team ({employees.length})</h2>

      {/* Mobile cards */}
      <div className="mobile-only emp-cards">
        {employees.map(emp => <EmpCard key={emp.id} emp={emp} />)}
        {!loading && employees.length === 0 && (
          <p style={{color:'#64748b', textAlign:'center', padding:'20px 0'}}>
            No employees yet. Tap + Register to add one.
          </p>
        )}
      </div>

      {/* Desktop table */}
      <div className="desktop-only table-scroll">
        <table>
          <thead>
            <tr>{['Name','ID','Department','Registered','Status','Actions'].map(h =>
              <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {employees.map((emp, i) => (
              <tr key={emp.id} className="table-row-click" style={{background: i%2===0 ? '#0f172a' : 'transparent'}}
                onClick={() => setSelected(emp)}>
                <td>{emp.name}</td>
                <td>{emp.employee_id}</td>
                <td>{emp.department || '-'}</td>
                <td>{emp.registered_at ? new Date(emp.registered_at).toLocaleDateString('en-GB') : '-'}</td>
                <td><span className={`badge ${emp.is_active ? 'badge-green' : 'badge-red'}`}>{emp.is_active ? 'Active' : 'Inactive'}</span></td>
                <td onClick={e => e.stopPropagation()}>
                  <button className="btn-primary btn-sm" style={{marginRight:6}} onClick={() => openEdit(emp)}>Edit</button>
                  <button className="btn-danger btn-sm" onClick={() => handleDelete(emp.employee_id, emp.name)}>Delete</button>
                </td>
              </tr>
            ))}
            {!loading && employees.length === 0 && (
              <tr><td colSpan={6} style={{textAlign:'center', color:'#64748b', padding:20}}>No employees registered yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <h2 className="section-title">Today&apos;s Attendance</h2>

      <div className="mobile-only">
        {logs.map((log, i) => (
          <div key={i} className="att-card">
            <div className="att-card-name">{log.employee_name}</div>
            <div className="att-card-meta">
              In: {log.check_in ? new Date(log.check_in).toLocaleTimeString('en-GB') : '-'}
              {log.check_out ? ` · Out: ${new Date(log.check_out).toLocaleTimeString('en-GB')}` : ''}
              {log.duration ? ` · ${log.duration}` : ''}
            </div>
            <span className={`badge ${log.check_out ? 'badge-gray' : 'badge-green'}`}>
              {log.check_out ? 'Completed' : 'In Office'}
            </span>
          </div>
        ))}
        {logs.length === 0 && <p style={{color:'#64748b', textAlign:'center'}}>No attendance today yet.</p>}
      </div>

      <div className="desktop-only table-scroll">
        <table>
          <thead>
            <tr>{['Name','ID','Department','Check In','Check Out','Duration','Status'].map(h =>
              <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {logs.map((log, i) => (
              <tr key={i} style={{background: i%2===0 ? '#0f172a' : 'transparent'}}>
                <td>{log.employee_name}</td>
                <td>{log.employee_id}</td>
                <td>{log.department || '-'}</td>
                <td>{log.check_in  ? new Date(log.check_in ).toLocaleTimeString('en-GB') : '-'}</td>
                <td>{log.check_out ? new Date(log.check_out).toLocaleTimeString('en-GB') : '-'}</td>
                <td>{log.duration || '-'}</td>
                <td><span className={`badge ${log.check_out ? 'badge-gray' : 'badge-green'}`}>{log.check_out ? 'Completed' : 'In Office'}</span></td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={7} style={{textAlign:'center', color:'#64748b', padding:20}}>No attendance today yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-title">{selected.name}</div>
            {[['Employee ID', selected.employee_id], ['Department', selected.department || 'N/A'],
              ['Status', selected.is_active ? 'Active' : 'Inactive'],
              ['Registered', selected.registered_at ? new Date(selected.registered_at).toLocaleString('en-GB') : '-'],
            ].map(([label, val]) => (
              <div key={label} className="detail-row">
                <span className="detail-label">{label}</span><span>{val}</span>
              </div>
            ))}
            <div className="modal-actions">
              <button className="btn-primary" onClick={() => openEdit(selected)}>Edit</button>
              <button className="btn-warning" onClick={() => toggleActive(selected)}>
                {selected.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button className="btn-danger" onClick={() => handleDelete(selected.employee_id, selected.name)}>Delete</button>
            </div>
            <button className="btn-secondary" style={{width:'100%', marginTop:10, padding:12}} onClick={() => setSelected(null)}>Close</button>
          </div>
        </div>
      )}

      {editing && (
        <div className="modal-overlay" onClick={() => !saving && setEditing(null)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-title">Edit Employee</div>
            <label className="field-label">Full Name</label>
            <input value={editForm.name} onChange={e => setEditForm({...editForm, name:e.target.value})} />
            <label className="field-label">Employee ID</label>
            <input value={editForm.employee_id} onChange={e => setEditForm({...editForm, employee_id:e.target.value})} />
            <label className="field-label">Department</label>
            <input value={editForm.department} onChange={e => setEditForm({...editForm, department:e.target.value})} />
            <div className="modal-actions">
              <button className="btn-success" onClick={saveEdit} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
              <button className="btn-secondary" onClick={() => setEditing(null)} disabled={saving}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
