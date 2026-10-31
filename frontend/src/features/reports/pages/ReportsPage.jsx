import { useQuery } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

const money = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0);

export function ReportsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['reports', 'dashboard'], queryFn: async () => (await apiClient.get('/reports/dashboard')).data });
  return <AppShell title="Reports" description="Billing, collections, subscription health and upcoming expiries." breadcrumb="Brightloop / Reports" activeNav="Reports">
    {isLoading && <p>Loading report…</p>}{error && <p role="alert">{error.response?.data?.detail || 'Could not load report.'}</p>}
    {data && <>
      <div className="data-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 20, padding: 20 }}>
        <div><span>Active subscriptions</span><h2>{data.active_subscriptions}</h2></div>
        <div><span>Monthly recurring revenue</span><h2>{money(data.mrr)}</h2></div>
        <div><span>Billed</span><h2>{money(data.billed)}</h2></div>
        <div><span>Collected</span><h2>{money(data.collected)}</h2></div>
        <div><span>Outstanding</span><h2>{money(data.outstanding)}</h2></div>
        <div><span>Overdue</span><h2>{data.overdue_count} · {money(data.overdue_total)}</h2></div>
      </div>
      <div className="data-card" style={{ marginTop: 20 }}><h2>Invoice health</h2><table className="data-table"><thead><tr><th>Status</th><th>Invoices</th><th>Total</th></tr></thead><tbody>
        {Object.entries(data.invoice_health).map(([status, metrics]) => <tr key={status}><td>{status.replaceAll('_', ' ')}</td><td>{metrics.count}</td><td>{money(metrics.total)}</td></tr>)}
      </tbody></table></div>
      <div className="data-card" style={{ marginTop: 20 }}><h2>Upcoming expiries</h2><table className="data-table"><thead><tr><th>Customer</th><th>Plan</th><th>Expiry</th><th>Amount</th></tr></thead><tbody>
        {data.upcoming_expiries.map((item, index) => <tr key={`${item.customer}-${item.expiry}-${index}`}><td>{item.customer}</td><td>{item.plan}</td><td>{item.expiry}</td><td>{money(item.amount)}</td></tr>)}
        {data.upcoming_expiries.length === 0 && <tr><td colSpan="4">No upcoming expiries.</td></tr>}
      </tbody></table></div>
    </>}
  </AppShell>;
}
