import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';
import apiClient from '../../../lib/apiClient';
import { InvoiceTable } from '../components/InvoiceTable.jsx';

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

export function InvoicesPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState('');
  const queryClient = useQueryClient();
  const { data: invoices = [], isLoading, error } = useQuery({ queryKey: ['invoices'], queryFn: async () => (await apiClient.get('/invoices')).data });
  const bill = useMutation({
    mutationFn: async () => (await apiClient.post('/billing/run')).data,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['invoices'] });
      setNotice(`Billing finished: ${result.created.length} invoice(s) created; ${result.already_billed} period(s) already billed.`);
    },
  });
  const invoiceAction = useMutation({
    mutationFn: async ({ id, action }) => (await apiClient.post(`/invoices/${id}/${action}`)).data,
    onSuccess: async (updated) => {
      await queryClient.invalidateQueries({ queryKey: ['invoices'] });
      setSelected(updated);
    },
  });
  const filtered = useMemo(() => invoices.filter((invoice) => {
    const matchesQuery = [invoice.invoiceNumber, invoice.customer, invoice.subscription].some((value) => (value || '').toLowerCase().includes(query.toLowerCase()));
    return matchesQuery && (status === 'All statuses' || invoice.status === status);
  }), [invoices, query, status]);

  return <AppShell title="Invoices" description="Invoices generated from due subscription periods." breadcrumb="Brightloop / Invoices" activeNav="invoices"
    primaryAction={<button className="primary-action" type="button" disabled={bill.isPending} onClick={() => bill.mutate()}>{bill.isPending ? 'Billing…' : 'Run billing'}</button>}>
    <div className="invoice-toolbar">
      <input className="invoice-search" type="search" placeholder="Search invoices..." aria-label="Search invoices" value={query} onChange={(event) => setQuery(event.target.value)} />
      <select className="invoice-filter" aria-label="Filter invoices by status" value={status} onChange={(event) => setStatus(event.target.value)}>
        <option>All statuses</option><option>Draft</option><option>Confirmed</option><option>Partially_Paid</option><option>Overdue</option><option>Paid</option>
      </select>
    </div>
    {notice && <div className="invoice-notice" role="status">{notice}</div>}
    {bill.error && <p role="alert">{bill.error.response?.data?.detail || 'Billing run failed.'}</p>}
    <div className="data-card invoice-card">
      {isLoading ? <p>Loading invoices…</p> : error ? <p role="alert">{error.response?.data?.detail || 'Could not load invoices.'}</p> : <InvoiceTable rows={filtered} onSelect={setSelected} />}
      <div className="table-footer">Showing {filtered.length} of {invoices.length} records</div>
    </div>
    <Drawer title={selected?.invoiceNumber || 'Invoice'} isOpen={Boolean(selected)} onClose={() => setSelected(null)} className="invoice-detail-drawer">
      {selected && <>
        <span className="status-pill"><span className="dot" />{selected.status}</span>
        <dl className="invoice-detail-list">
          <div><dt>Invoice</dt><dd>{selected.invoiceNumber}</dd></div><div><dt>Customer</dt><dd>{selected.customer}</dd></div><div><dt>Subscription</dt><dd>{selected.subscription}</dd></div>
          <div><dt>Date</dt><dd>{selected.date}</dd></div><div><dt>Due</dt><dd>{selected.due}</dd></div><div><dt>Total</dt><dd>{currency.format(selected.total)}</dd></div>
          <div><dt>Paid</dt><dd>{currency.format(selected.amount_paid)}</dd></div><div><dt>Balance due</dt><dd>{currency.format(selected.balance_due)}</dd></div>
        </dl>
        <div className="drawer-actions">
          {selected.status === 'Draft' && <button className="primary-action" type="button" disabled={invoiceAction.isPending} onClick={() => invoiceAction.mutate({ id: selected.id, action: 'confirm' })}>Confirm</button>}
          {['Confirmed', 'Partially_Paid', 'Overdue'].includes(selected.status) && <button className="secondary-action" type="button" disabled={invoiceAction.isPending} onClick={() => invoiceAction.mutate({ id: selected.id, action: 'send' })}>Send invoice</button>}
          {invoiceAction.error && <p role="alert">{invoiceAction.error.response?.data?.detail || 'Could not update invoice.'}</p>}
        </div>
      </>}
    </Drawer>
  </AppShell>;
}
