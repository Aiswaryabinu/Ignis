import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';
import apiClient from '../../../lib/apiClient';

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const payable = (invoice) => ['Confirmed', 'Partially_Paid', 'Overdue'].includes(invoice.status);

export function PaymentsPage() {
  const [query, setQuery] = useState('');
  const [isRecordOpen, setRecordOpen] = useState(false);
  const queryClient = useQueryClient();
  const { data: payments = [], isLoading, error } = useQuery({ queryKey: ['payments'], queryFn: async () => (await apiClient.get('/payments')).data });
  const { data: invoices = [] } = useQuery({ queryKey: ['invoices'], queryFn: async () => (await apiClient.get('/invoices')).data });
  const createPayment = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/payments', payload)).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['payments'] }),
        queryClient.invalidateQueries({ queryKey: ['invoices'] }),
      ]);
      setRecordOpen(false);
    },
  });
  const filtered = useMemo(() => payments.filter((payment) =>
    [payment.reference, payment.invoice, payment.note, payment.customer].some((value) => (value || '').toLowerCase().includes(query.toLowerCase()))), [payments, query]);

  function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const invoice = invoices.find((item) => item.id === form.get('invoice_id'));
    createPayment.mutate({
      customer_id: invoice.customer_id,
      payment_method: form.get('payment_method'),
      amount: form.get('amount'),
      payment_date: form.get('payment_date') || null,
      reference_number: form.get('reference_number') || null,
      notes: form.get('notes') || null,
      allocations: [{ invoice_id: invoice.id, amount: form.get('amount') }],
    });
  }

  return <AppShell title="Payments" description="Record received payments and allocate them to invoices." breadcrumb="Brightloop / Payments" activeNav="payments"
    primaryAction={<button className="primary-action" type="button" onClick={() => setRecordOpen(true)}>+ Record payment</button>}>
    <div className="payment-toolbar"><input className="payment-search" type="search" placeholder="Search payments..." aria-label="Search payments" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
    <div className="data-card payment-card"><table className="data-table payment-table"><thead><tr><th>Reference</th><th>Customer</th><th>Invoice</th><th>Method</th><th className="amount-column">Amount</th><th>Date</th><th>Note</th><th>Status</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="8">Loading payments…</td></tr>}{error && <tr><td colSpan="8" role="alert">{error.response?.data?.detail || 'Could not load payments.'}</td></tr>}
      {!isLoading && !error && filtered.map((payment) => <tr key={payment.id}><td className="table-link">{payment.reference}</td><td>{payment.customer}</td><td>{payment.invoice}</td><td>{payment.method}</td><td className="amount-column">{currency.format(payment.amount)}</td><td>{payment.date}</td><td>{payment.note}</td><td>{payment.status}</td></tr>)}
      {!isLoading && !error && filtered.length === 0 && <tr><td colSpan="8">No payments found.</td></tr>}
    </tbody></table><div className="table-footer">Showing {filtered.length} of {payments.length} records</div></div>
    <Drawer title="Record payment" isOpen={isRecordOpen} onClose={() => setRecordOpen(false)} className="form-drawer">
      <form className="drawer-form" onSubmit={submit}>
        <label className="drawer-field"><span className="drawer-field-label">Invoice</span><select name="invoice_id" className="drawer-input" required defaultValue="">
          <option value="" disabled>Select an unpaid invoice</option>{invoices.filter(payable).map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoiceNumber} · {invoice.customer} · balance {currency.format(invoice.balance_due)}</option>)}
        </select></label>
        <label className="drawer-field"><span className="drawer-field-label">Method</span><select name="payment_method" className="drawer-input"><option value="UPI">UPI</option><option value="BANK_TRANSFER">Bank transfer</option><option value="CARD">Card</option><option value="CASH">Cash</option><option value="OTHER">Other</option></select></label>
        <label className="drawer-field"><span className="drawer-field-label">Amount (₹)</span><input name="amount" type="number" min="0.01" step="0.01" className="drawer-input" required /></label>
        <label className="drawer-field"><span className="drawer-field-label">Date</span><input name="payment_date" type="date" className="drawer-input" /></label>
        <label className="drawer-field"><span className="drawer-field-label">Reference</span><input name="reference_number" className="drawer-input" /></label>
        <label className="drawer-field"><span className="drawer-field-label">Note</span><input name="notes" className="drawer-input" /></label>
        {createPayment.error && <p role="alert">{createPayment.error.response?.data?.detail || 'Could not save payment.'}</p>}
        <button className="primary-action drawer-submit" type="submit" disabled={createPayment.isPending || !invoices.some(payable)}>{createPayment.isPending ? 'Saving…' : 'Save payment'}</button>
      </form>
    </Drawer>
  </AppShell>;
}
