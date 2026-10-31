import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

const pillClass = { Active: 'success', Confirmed: 'info', Quotation: 'info', Paused: 'warning', Closed: 'muted' };

export function SubscriptionsPage() {
  const [selected, setSelected] = useState(null);
  const queryClient = useQueryClient();
  const { data: subscriptions = [], isLoading, error } = useQuery({ queryKey: ['subscriptions'], queryFn: async () => (await apiClient.get('/subscriptions')).data });
  const transition = useMutation({
    mutationFn: async ({ id, action }) => (await apiClient.post(`/subscriptions/${id}/${action}`, {})).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      setSelected(null);
    },
  });

  return <AppShell title="Subscriptions" description="Subscriptions created from accepted quotations and their lifecycle." breadcrumb="Brightloop / Subscriptions" activeNav="Subscriptions"
    primaryAction={<a className="primary-action" href="/quotations">Create from quotation</a>}>
    <div className="data-card"><table className="data-table"><thead><tr><th>Subscription</th><th>Customer</th><th>Plan</th><th>Start</th><th>Expiry</th><th>Payment terms</th><th>Status</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="7">Loading subscriptions…</td></tr>}{error && <tr><td colSpan="7" role="alert">{error.response?.data?.detail || 'Could not load subscriptions.'}</td></tr>}
      {!isLoading && !error && subscriptions.map((item) => <tr key={item.id} className="customer-row" onClick={() => setSelected(item)}>
        <td className="customer-name">{item.number}</td><td>{item.customer}</td><td>{item.plan}</td><td>{item.start}</td><td>{item.expiry}</td><td>{item.terms}</td>
        <td><span className={`status-pill ${pillClass[item.status] || 'muted'}`}><span className="dot" />{item.status}</span></td>
      </tr>)}
      {!isLoading && !error && subscriptions.length === 0 && <tr><td colSpan="7">No subscriptions yet. Accept a sent quotation to create one.</td></tr>}
    </tbody></table><div className="table-footer">{subscriptions.length} subscriptions</div></div>
    {selected && <div className="data-card" style={{ marginTop: 16, padding: 20 }}>
      <h2>{selected.number} · {selected.customer}</h2><p>{selected.plan} · {selected.start} – {selected.expiry} · {selected.terms}</p>
      <p>Status: <span className={`status-pill ${pillClass[selected.status] || 'muted'}`}><span className="dot" />{selected.status}</span></p>
      {selected.status === 'Confirmed' && <button className="primary-action" type="button" disabled={transition.isPending} onClick={() => transition.mutate({ id: selected.id, action: 'activate' })}>Activate</button>}
      {selected.status === 'Active' && <button className="secondary-action" type="button" disabled={transition.isPending} onClick={() => transition.mutate({ id: selected.id, action: 'pause' })}>Pause</button>}
      {selected.status === 'Paused' && <button className="primary-action" type="button" disabled={transition.isPending} onClick={() => transition.mutate({ id: selected.id, action: 'resume' })}>Resume</button>}
      {['Active', 'Paused', 'Confirmed', 'Quotation'].includes(selected.status) && <button className="secondary-action" type="button" disabled={transition.isPending} onClick={() => transition.mutate({ id: selected.id, action: 'close' })}>Close subscription</button>}
      <button className="drawer-cancel-btn" type="button" onClick={() => setSelected(null)}>Dismiss</button>
      {transition.error && <p role="alert">{transition.error.response?.data?.detail || 'Could not update subscription.'}</p>}
    </div>}
  </AppShell>;
}
