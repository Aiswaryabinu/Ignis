import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

export function PlansPage() {
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const queryClient = useQueryClient();
  const { data: plans = [], isLoading, error } = useQuery({ queryKey: ['plans'], queryFn: async () => (await apiClient.get('/plans')).data });
  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: async () => (await apiClient.get('/products')).data });
  const createPlan = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/plans', payload)).data,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['plans'] }); setDrawerMode(null); },
  });

  useEffect(() => {
    const panel = document.querySelector('.main-panel');
    if (!panel) return undefined;
    panel.classList.toggle('drawer-push', drawerMode !== null);
    return () => panel.classList.remove('drawer-push');
  }, [drawerMode]);

  function submitPlan(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createPlan.mutate({
      name: form.get('name').trim(), product_id: form.get('product_id') || null,
      billing_interval: form.get('billing_interval').toUpperCase(), price: form.get('price'),
      minimum_quantity: form.get('minimum_quantity'), allow_renewal: form.get('allow_renewal') === 'true',
    });
  }

  return <AppShell title="Subscription Plans" description="Configure pricing, billing frequencies, and plan rules." breadcrumb="Brightloop / Subscription Plans" activeNav="Subscription Plans"
    primaryAction={<button className="primary-action" type="button" onClick={() => setDrawerMode('create')}>+ Create plan</button>}>
    <aside className={`customer-drawer ${drawerMode ? 'customer-drawer--open' : ''}`}>
      {drawerMode === 'create' && <>
        <div className="drawer-header"><div className="drawer-title-group"><span className="drawer-eyebrow">New Record</span><h2 className="drawer-title">Create plan</h2></div><button type="button" className="drawer-close-btn" onClick={() => setDrawerMode(null)} aria-label="Close">✕</button></div>
        <div className="drawer-divider" /><p className="drawer-subtitle">Set the product, price, billing interval and renewal behavior.</p>
        <form className="drawer-form" onSubmit={submitPlan}>
          <label className="drawer-field"><span className="drawer-field-label">Plan name</span><input name="name" className="drawer-input" required /></label>
          <label className="drawer-field"><span className="drawer-field-label">Product</span><select name="product_id" className="drawer-input" defaultValue=""><option value="">No product linked</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label>
          <label className="drawer-field"><span className="drawer-field-label">Billing interval</span><select name="billing_interval" className="drawer-input"><option value="MONTHLY">Monthly</option><option value="YEARLY">Yearly</option><option value="WEEKLY">Weekly</option><option value="DAILY">Daily</option></select></label>
          <label className="drawer-field"><span className="drawer-field-label">Price (₹)</span><input name="price" type="number" min="0" step="0.01" className="drawer-input" required /></label>
          <label className="drawer-field"><span className="drawer-field-label">Minimum quantity</span><input name="minimum_quantity" type="number" min="1" step="1" defaultValue="1" className="drawer-input" required /></label>
          <label className="drawer-field"><span className="drawer-field-label">Renewal</span><select name="allow_renewal" className="drawer-input"><option value="true">Automatic</option><option value="false">Manual</option></select></label>
          {createPlan.error && <p role="alert">{createPlan.error.response?.data?.detail || 'Could not save plan.'}</p>}
          <div className="drawer-actions"><button type="submit" className="drawer-save-btn" disabled={createPlan.isPending}>{createPlan.isPending ? 'Saving…' : 'Save plan'}</button><button type="button" className="drawer-cancel-btn" onClick={() => setDrawerMode(null)}>Cancel</button></div>
        </form>
      </>}
      {drawerMode === 'detail' && selectedPlan && <>
        <div className="drawer-header"><div className="drawer-title-group"><span className="drawer-eyebrow">Plan · {selectedPlan.status}</span><h2 className="drawer-title">{selectedPlan.plan}</h2></div><button type="button" className="drawer-close-btn" onClick={() => setDrawerMode(null)} aria-label="Close">✕</button></div>
        <div className="drawer-divider" /><div className="drawer-detail-grid">
          <div className="drawer-detail-item"><span className="drawer-detail-key">Product</span><span className="drawer-detail-val">{selectedPlan.product}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Billing</span><span className="drawer-detail-val">{selectedPlan.billing}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Price</span><span className="drawer-detail-val">{currency.format(selectedPlan.price)}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Minimum quantity</span><span className="drawer-detail-val">{selectedPlan.minQty}</span></div>
          <div className="drawer-detail-item"><span className="drawer-detail-key">Renewal</span><span className="drawer-detail-val">{selectedPlan.renewal}</span></div>
        </div>
      </>}
    </aside>
    <div className="customers-layout"><div className="customers-list-panel"><div className="data-card"><table className="data-table"><thead><tr><th>Plan</th><th>Product</th><th>Billing</th><th>Base price</th><th>Min qty</th><th>Renewal</th><th>Status</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="7">Loading plans…</td></tr>}{error && <tr><td colSpan="7" role="alert">{error.response?.data?.detail || 'Could not load plans.'}</td></tr>}
      {!isLoading && !error && plans.map((plan) => <tr key={plan.id} className="customer-row" onClick={() => { setSelectedPlan(plan); setDrawerMode('detail'); }}><td>{plan.plan}</td><td>{plan.product}</td><td>{plan.billing}</td><td>{currency.format(plan.price)}</td><td>{plan.minQty}</td><td>{plan.renewal}</td><td><span className={`status-pill ${plan.status === 'Active' ? 'success' : 'warning'}`}><span className="dot" />{plan.status}</span></td></tr>)}
      {!isLoading && !error && plans.length === 0 && <tr><td colSpan="7">No plans yet.</td></tr>}
    </tbody></table><div className="table-footer">{plans.length} plans</div></div></div></div>
  </AppShell>;
}
