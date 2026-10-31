import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { downloadCsv } from '../../../lib/exportCsv.js';

const plans = [
  { name: 'Scale Annual', billed: '₹5,09,760', collected: '₹0', outstanding: '₹5,09,760' },
  { name: 'Business Monthly', billed: '₹3,27,450', collected: '₹1,09,150', outstanding: '₹2,18,300' },
  { name: 'Starter Monthly', billed: '₹8,850', collected: '₹8,850', outstanding: '₹0' },
];

export function ReportsPage() {
  const [period, setPeriod] = useState('This month');
  const [plan, setPlan] = useState('All plans');
  const visiblePlans = useMemo(() => plan === 'All plans' ? plans : plans.filter((item) => item.name === plan), [plan]);
  const exportReport = () => downloadCsv('revenue-report.csv', visiblePlans);

  return (
    <AppShell title="Reports" description="Revenue, payments and overdue invoices." breadcrumb="Brightloop / Reports" activeNav="reports" secondaryAction={<button className="secondary-action" type="button" onClick={exportReport}>Export</button>}>
      <div className="report-toolbar">
        <select value={period} onChange={(event) => setPeriod(event.target.value)} aria-label="Report period"><option>This month</option><option>Last 3 months</option><option>This year</option></select>
        <select value={plan} onChange={(event) => setPlan(event.target.value)} aria-label="Filter by plan"><option>All plans</option><option>Business Monthly</option><option>Scale Annual</option><option>Secure Weekly</option><option>Starter Monthly</option></select>
      </div>
      <div className="metric-grid report-metrics">
        <div className="metric-card"><span>Active subscriptions</span><strong>2</strong></div>
        <div className="metric-card"><span>Monthly recurring revenue</span><strong>₹1,10,500</strong></div>
        <div className="metric-card"><span>Collected</span><strong>₹2,18,000</strong></div>
        <div className="metric-card"><span>Outstanding</span><strong>₹2,64,030</strong></div>
        <div className="metric-card danger-metric"><span>Overdue invoices</span><strong>1</strong></div>
      </div>
      <div className="data-card report-card">
        <table className="data-table report-table"><thead><tr><th>Plan</th><th className="amount-column">Billed</th><th className="amount-column">Collected</th><th className="amount-column">Outstanding</th></tr></thead><tbody>{visiblePlans.map((item) => <tr key={item.name}><td className="table-link">{item.name}</td><td className="amount-column">{item.billed}</td><td className="amount-column">{item.collected}</td><td className="amount-column">{item.outstanding}</td></tr>)}</tbody></table>
      </div>
    </AppShell>
  );
}
