import { useState, useEffect } from 'react'
import { Plus, Trash2, CheckCircle2, XCircle } from 'lucide-react'

interface Supplier {
  id: number
  name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  address: string | null
  is_active: boolean
}

function App() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [name, setName] = useState('')
  const [contactName, setContactName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // API Base URL (Vite proxy redirects /api to backend)
  const API_URL = '/api/suppliers'

  useEffect(() => {
    fetchSuppliers()
  }, [])

  const fetchSuppliers = async () => {
    try {
      setLoading(true)
      const res = await fetch(API_URL)
      if (!res.ok) throw new Error('Failed to fetch suppliers')
      const data = await res.json()
      setSuppliers(data)
      setError(null)
    } catch (err: any) {
      // If server is not running or proxy fails, fallback to checking port 8000 directly
      try {
        const res = await fetch('http://localhost:8000/suppliers')
        if (!res.ok) throw new Error('Backend server is down')
        const data = await res.json()
        setSuppliers(data)
        setError(null)
      } catch (directErr) {
        setError('Could not connect to the Backend API. Please make sure the FastAPI server is running on port 8000.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleAddSupplier = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    const newSupplier = {
      name,
      contact_name: contactName || null,
      email: email || null,
      phone: phone || null,
      address: address || null,
      is_active: true
    }

    try {
      // Try both proxied /api/suppliers and direct backend URL
      let res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSupplier)
      })

      if (!res.ok && res.status === 404) {
        res = await fetch('http://localhost:8000/suppliers/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newSupplier)
        })
      }

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || 'Failed to add supplier')
      }

      setName('')
      setContactName('')
      setEmail('')
      setPhone('')
      setAddress('')
      fetchSuppliers()
    } catch (err: any) {
      alert(err.message)
    }
  }

  const handleDeleteSupplier = async (id: number) => {
    if (!confirm('Are you sure you want to delete this supplier?')) return

    try {
      let res = await fetch(`${API_URL}/${id}`, {
        method: 'DELETE'
      })

      if (!res.ok && res.status === 404) {
        res = await fetch(`http://localhost:8000/suppliers/${id}`, {
          method: 'DELETE'
        })
      }

      if (!res.ok) throw new Error('Failed to delete supplier')
      fetchSuppliers()
    } catch (err: any) {
      alert(err.message)
    }
  }

  return (
    <div className="app-container">
      <header style={{ marginBottom: '2rem', borderBottom: '1px solid #eee', paddingBottom: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '2.5rem', color: '#646cff' }}>Supply Chain Management</h1>
        <p style={{ margin: '0.5rem 0 0 0', opacity: 0.7 }}>Collaborative Workspace Boilerplate</p>
      </header>

      <main style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        {/* Form Column */}
        <section style={{ backgroundColor: '#f9f9f9', padding: '1.5rem', borderRadius: '8px', border: '1px solid #eaeaea', height: 'fit-content' }}>
          <h2 style={{ marginTop: 0, fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Plus size={20} /> Add Supplier
          </h2>
          <form onSubmit={handleAddSupplier}>
            <div className="form-group">
              <label>Company Name *</label>
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                required 
                placeholder="Acme Corp"
              />
            </div>
            <div className="form-group">
              <label>Contact Person</label>
              <input 
                type="text" 
                value={contactName} 
                onChange={(e) => setContactName(e.target.value)} 
                placeholder="John Doe"
              />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input 
                type="email" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                placeholder="john@acme.com"
              />
            </div>
            <div className="form-group">
              <label>Phone</label>
              <input 
                type="text" 
                value={phone} 
                onChange={(e) => setPhone(e.target.value)} 
                placeholder="+1 555-0199"
              />
            </div>
            <div className="form-group">
              <label>Address</label>
              <input 
                type="text" 
                value={address} 
                onChange={(e) => setAddress(e.target.value)} 
                placeholder="123 Industrial Parkway"
              />
            </div>
            <button type="submit" className="btn-primary" style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '1rem' }}>
              Create Supplier
            </button>
          </form>
        </section>

        {/* Suppliers List Column */}
        <section>
          <h2 style={{ marginTop: 0, fontSize: '1.5rem' }}>Supplier Records</h2>
          
          {error && (
            <div style={{ padding: '1rem', backgroundColor: '#fee2e2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: '6px', marginBottom: '1rem' }}>
              {error}
            </div>
          )}

          {loading ? (
            <p>Loading suppliers...</p>
          ) : suppliers.length === 0 ? (
            <p style={{ opacity: 0.6 }}>No suppliers found. Use the form to add one!</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
              {suppliers.map((supplier) => (
                <div key={supplier.id} className="supplier-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {supplier.name}
                      {supplier.is_active ? (
                        <span style={{ fontSize: '0.75rem', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                          <CheckCircle2 size={12} /> Active
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: '#dc2626', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                          <XCircle size={12} /> Inactive
                        </span>
                      )}
                    </h3>
                    <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>
                      {supplier.contact_name && <p style={{ margin: '0.2rem 0' }}><strong>Contact:</strong> {supplier.contact_name}</p>}
                      {supplier.email && <p style={{ margin: '0.2rem 0' }}><strong>Email:</strong> {supplier.email}</p>}
                      {supplier.phone && <p style={{ margin: '0.2rem 0' }}><strong>Phone:</strong> {supplier.phone}</p>}
                      {supplier.address && <p style={{ margin: '0.2rem 0' }}><strong>Address:</strong> {supplier.address}</p>}
                    </div>
                  </div>
                  <button 
                    onClick={() => handleDeleteSupplier(supplier.id)} 
                    style={{ background: 'none', border: 'none', padding: '0.5rem', color: '#dc2626', cursor: 'pointer' }}
                    title="Delete supplier"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
