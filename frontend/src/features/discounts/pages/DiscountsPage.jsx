import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';
import apiClient from '../../../lib/apiClient';

export function DiscountsPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const queryClient = useQueryClient();
  const { data: discounts = [], isLoading, error } = useQuery({ queryKey: ['discounts'], queryFn: async () => (await apiClient.get('/discounts')).data });
  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: async () => (await apiClient.get('/products')).data });
  const createDiscount = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/discounts', payload)).data,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['discounts'] }); setCreateOpen(false); },
  });
  const filtered = useMemo(() => discounts.filter((item) => item.code.toLowerCase().includes(query.toLowerCase()) && (status === 'All statuses' || item.status === status)), [discounts, query, status]);

  function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const type = form.get('discount_type');
    createDiscount.mutate({
      code: form.get('code').trim().toUpperCase(), name: form.get('code').trim().toUpperCase(),
      discount_type: type, value: form.get('value'), min_purchase: form.get('min_purchase') || '0',
      min_quantity: form.get('min_quantity') || '1', start_date: form.get('start_date'),
      end_date: form.get('end_date') || null, usage_limit: form.get('usage_limit') || null,
      scope: form.get('scope'), product_id: form.get('product_id') || null,
    });
  }

  return <AppShell title="Discounts" description="Rules applied automatically to eligible invoices." breadcrumb="Brightloop / Discounts" activeNav="discounts" primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ Create discount</button>}>
    <div className="discount-toolbar">
      <input className="discount-search" type="search" placeholder="Search discounts..." aria-label="Search discounts" value={query} onChange={(event) => setQuery(event.target.value)} />
      <select className="discount-filter" aria-label="Filter discounts by status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Active</option><option>Draft</option><option>Expired</option><option>Inactive</option></select>
    </div>
    <div className="data-card discount-card"><table className="data-table discount-table"><thead><tr><th>Code</th><th>Type</th><th>Value</th><th>Minimum</th><th>Valid</th><th>Used</th><th>Applies to</th><th>Status</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="8">Loading discounts…</td></tr>}{error && <tr><td colSpan="8" role="alert">{error.response?.data?.detail || 'Could not load discounts.'}</td></tr>}
      {!isLoading && !error && filtered.map((item) => <tr key={item.id}><td className="table-link">{item.code}</td><td>{item.type}</td><td>{item.formatted_value}</td><td>{item.minimum}</td><td>{item.valid}</td><td>{item.used}</td><td>{item.applies_to}</td><td><span className={`status-pill ${item.status === 'Active' ? 'success' : item.status === 'Draft' ? 'warning' : 'muted'}`}><span className="dot" />{item.status}</span></td></tr>)}
      {!isLoading && !error && filtered.length === 0 && <tr><td colSpan="8">No discounts found.</td></tr>}
    </tbody></table><div className="table-footer">Showing {filtered.length} of {discounts.length} records</div></div>
    <Drawer title="Create discount" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer">
      <form className="drawer-form" onSubmit={submit}>
        <label className="drawer-field"><span className="drawer-field-label">Code</span><input name="code" className="drawer-input" required /></label>
        <label className="drawer-field"><span className="drawer-field-label">Type</span><select name="discount_type" className="drawer-input"><option value="PERCENTAGE">Percentage</option><option value="FIXED">Fixed amount</option></select></label>
        <label className="drawer-field"><span className="drawer-field-label">Value</span><input name="value" type="number" min="0.01" step="0.01" className="drawer-input" required /></label>
        <label className="drawer-field"><span className="drawer-field-label">Minimum purchase (₹)</span><input name="min_purchase" type="number" min="0" step="0.01" defaultValue="0" className="drawer-input" /></label>
        <label className="drawer-field"><span className="drawer-field-label">Minimum quantity</span><input name="min_quantity" type="number" min="1" defaultValue="1" className="drawer-input" /></label>
        <label className="drawer-field"><span className="drawer-field-label">Start date</span><input name="start_date" type="date" className="drawer-input" required /></label>
        <label className="drawer-field"><span className="drawer-field-label">End date</span><input name="end_date" type="date" className="drawer-input" /></label>
        <label className="drawer-field"><span className="drawer-field-label">Usage limit</span><input name="usage_limit" type="number" min="1" className="drawer-input" /></label>
        <label className="drawer-field"><span className="drawer-field-label">Applies to</span><select name="scope" className="drawer-input"><option value="SUBSCRIPTION">All subscriptions</option><option value="PRODUCT">Specific product</option></select></label>
        <label className="drawer-field"><span className="drawer-field-label">Product (for specific product)</span><select name="product_id" className="drawer-input" defaultValue=""><option value="">Select a product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label>
        {createDiscount.error && <p role="alert">{createDiscount.error.response?.data?.detail || 'Could not save discount.'}</p>}
        <button className="primary-action drawer-submit" type="submit" disabled={createDiscount.isPending}>{createDiscount.isPending ? 'Saving…' : 'Save discount'}</button>
      </form>
    </Drawer>
  </AppShell>;
}
