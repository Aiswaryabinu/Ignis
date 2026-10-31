import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

export function ProductsPage() {
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const queryClient = useQueryClient();
  const { data: products = [], isLoading, error } = useQuery({ queryKey: ['products'], queryFn: async () => (await apiClient.get('/products')).data });
  const createProduct = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/products', payload)).data,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['products'] }); setDrawerMode(null); },
  });

  useEffect(() => {
    const panel = document.querySelector('.main-panel');
    if (!panel) return undefined;
    panel.classList.toggle('drawer-push', drawerMode !== null);
    return () => panel.classList.remove('drawer-push');
  }, [drawerMode]);

  function submitProduct(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createProduct.mutate({ name: form.get('name').trim(), product_type: form.get('product_type'), sales_price: form.get('sales_price'), cost_price: form.get('cost_price') });
  }

  return <AppShell title="Products" description="What you sell, with cost, price and variants." breadcrumb="Brightloop / Products" activeNav="products"
    primaryAction={<button className="primary-action" type="button" onClick={() => setDrawerMode('create')}>+ Create</button>}>
    <aside className={`customer-drawer ${drawerMode ? 'customer-drawer--open' : ''}`}>
      {drawerMode === 'create' && <>
        <div className="drawer-header"><div className="drawer-title-group"><span className="drawer-eyebrow">New Record</span><h2 className="drawer-title">Create Product</h2></div><button type="button" className="drawer-close-btn" onClick={() => setDrawerMode(null)} aria-label="Close">✕</button></div>
        <div className="drawer-divider" /><p className="drawer-subtitle">Add product details and pricing.</p>
        <form className="drawer-form" onSubmit={submitProduct}>
          <label className="drawer-field"><span className="drawer-field-label">Name</span><input name="name" className="drawer-input" required /></label>
          <label className="drawer-field"><span className="drawer-field-label">Type</span><select name="product_type" className="drawer-input"><option>Software</option><option>Add-on</option><option>Hardware</option></select></label>
          <label className="drawer-field"><span className="drawer-field-label">Sales price (₹)</span><input name="sales_price" type="number" min="0" step="0.01" className="drawer-input" required /></label>
          <label className="drawer-field"><span className="drawer-field-label">Cost price (₹)</span><input name="cost_price" type="number" min="0" step="0.01" className="drawer-input" required /></label>
          {createProduct.error && <p role="alert">{createProduct.error.response?.data?.detail || 'Could not save product.'}</p>}
          <div className="drawer-actions"><button type="submit" className="drawer-save-btn" disabled={createProduct.isPending}>{createProduct.isPending ? 'Saving…' : 'Save Product'}</button><button type="button" className="drawer-cancel-btn" onClick={() => setDrawerMode(null)}>Cancel</button></div>
        </form>
      </>}
      {drawerMode === 'detail' && selectedProduct && <>
        <div className="drawer-header"><div className="drawer-title-group"><span className="drawer-eyebrow">{selectedProduct.type}</span><h2 className="drawer-title">{selectedProduct.name}</h2></div><button type="button" className="drawer-close-btn" onClick={() => setDrawerMode(null)} aria-label="Close">✕</button></div>
        <div className="drawer-divider" /><div className="drawer-detail-grid">
          <div className="drawer-detail-item"><span className="drawer-detail-key">Status</span><span className="drawer-detail-val">{selectedProduct.status}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Sales price</span><span className="drawer-detail-val">{currency.format(selectedProduct.sales_price)}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Cost price</span><span className="drawer-detail-val">{currency.format(selectedProduct.cost_price)}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Variants</span><span className="drawer-detail-val">{selectedProduct.variants}</span></div>
        </div>
      </>}
    </aside>
    <div className="customers-layout"><div className="customers-list-panel"><div className="data-card"><table className="data-table"><thead><tr><th>Product</th><th>Type</th><th>Sales price</th><th>Cost price</th><th>Variants</th><th>Status</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="6">Loading products…</td></tr>}{error && <tr><td colSpan="6" role="alert">{error.response?.data?.detail || 'Could not load products.'}</td></tr>}
      {!isLoading && !error && products.map((product) => <tr key={product.id} className="customer-row" onClick={() => { setSelectedProduct(product); setDrawerMode('detail'); }}><td className="product-name">{product.name}</td><td>{product.type}</td><td>{currency.format(product.sales_price)}</td><td>{currency.format(product.cost_price)}</td><td>{product.variants}</td><td><span className={`status-pill ${product.status === 'Active' ? 'success' : 'muted'}`}><span className="dot" />{product.status}</span></td></tr>)}
      {!isLoading && !error && products.length === 0 && <tr><td colSpan="6">No products yet.</td></tr>}
    </tbody></table><div className="table-footer">{products.length} products</div></div></div></div>
  </AppShell>;
}
