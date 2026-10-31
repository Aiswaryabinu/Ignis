import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

export function QuotationsPage() {
  const [creating, setCreating] = useState(false);
  const queryClient = useQueryClient();
  const { data: quotes = [], isLoading, error } = useQuery({ queryKey: ['quotations'], queryFn: async () => (await apiClient.get('/quotations')).data });
  const { data: customers = [] } = useQuery({ queryKey: ['customers'], queryFn: async () => (await apiClient.get('/customers')).data });
  const { data: plans = [] } = useQuery({ queryKey: ['plans'], queryFn: async () => (await apiClient.get('/plans')).data });
  const createQuote = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/quotations', payload)).data,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['quotations'] }); setCreating(false); },
  });
  const action = useMutation({
    mutationFn: async ({ id, operation }) => (await apiClient.post(`/quotations/${id}/${operation}`)).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['quotations'] }),
        queryClient.invalidateQueries({ queryKey: ['subscriptions'] }),
      ]);
    },
  });

  function submitQuote(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createQuote.mutate({ customer_id: form.get('customer_id'), plan_id: form.get('plan_id'), quantity: Number(form.get('quantity')), valid_days: Number(form.get('valid_days')) });
  }

  return <AppShell title="Quotations" description="Create offers, send them, and convert accepted quotations into subscriptions." breadcrumb="Brightloop / Quotations" activeNav="Quotations"
    primaryAction={<button className="primary-action" type="button" onClick={() => setCreating(true)}>+ New quotation</button>}>
    {creating && <div className="data-card" style={{ padding: 20, marginBottom: 20 }}><form className="drawer-form" onSubmit={submitQuote}>
      <label className="drawer-field"><span className="drawer-field-label">Customer</span><select name="customer_id" className="drawer-input" required defaultValue="">{customers.length === 0 && <option value="">No customers available</option>}<option value="" disabled>Select a customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label>
      <label className="drawer-field"><span className="drawer-field-label">Plan</span><select name="plan_id" className="drawer-input" required defaultValue="">{plans.length === 0 && <option value="">No plans available</option>}<option value="" disabled>Select a plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name} · {currency.format(plan.price)} / {plan.billing}</option>)}</select></label>
      <label className="drawer-field"><span className="drawer-field-label">Quantity</span><input name="quantity" type="number" min="1" defaultValue="1" className="drawer-input" required /></label>
      <label className="drawer-field"><span className="drawer-field-label">Valid for (days)</span><input name="valid_days" type="number" min="1" max="365" defaultValue="30" className="drawer-input" required /></label>
      {createQuote.error && <p role="alert">{createQuote.error.response?.data?.detail || 'Could not create quotation.'}</p>}
      <div className="drawer-actions"><button className="drawer-save-btn" disabled={createQuote.isPending || customers.length === 0 || plans.length === 0}>{createQuote.isPending ? 'Creating…' : 'Create quotation'}</button><button className="drawer-cancel-btn" type="button" onClick={() => setCreating(false)}>Cancel</button></div>
    </form></div>}
    <div className="data-card"><table className="data-table"><thead><tr><th>Quotation</th><th>Customer</th><th>Plan</th><th>Items</th><th>Valid until</th><th>Total</th><th>Status / Actions</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="7">Loading quotations…</td></tr>}{error && <tr><td colSpan="7" role="alert">{error.response?.data?.detail || 'Could not load quotations.'}</td></tr>}
      {!isLoading && !error && quotes.map((quote) => <tr key={quote.id}>
        <td className="customer-name">{quote.number}</td><td>{quote.customer}</td><td>{quote.plan}</td><td>{quote.lines}</td><td>{quote.valid_until}</td><td>{currency.format(quote.grand_total)}</td>
        <td><span className={`status-pill ${quote.status === 'Accepted' ? 'success' : quote.status === 'Draft' ? 'warning' : 'info'}`}><span className="dot" />{quote.status}</span>
          {quote.status === 'Draft' && <button type="button" className="secondary-action" disabled={action.isPending} onClick={() => action.mutate({ id: quote.id, operation: 'send' })}>Send</button>}
          {quote.status === 'Sent' && <button type="button" className="secondary-action" disabled={action.isPending} onClick={() => action.mutate({ id: quote.id, operation: 'accept' })}>Accept & create subscription</button>}
        </td>
      </tr>)}
      {!isLoading && !error && quotes.length === 0 && <tr><td colSpan="7">No quotations yet.</td></tr>}
    </tbody></table><div className="table-footer">{quotes.length} quotations</div></div>
    {action.error && <p role="alert">{action.error.response?.data?.detail || 'Quotation action failed.'}</p>}
  </AppShell>;
}
