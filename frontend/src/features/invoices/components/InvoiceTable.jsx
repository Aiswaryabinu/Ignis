const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const statusClass = {
  Draft: 'warning',
  Overdue: 'danger',
  Confirmed: 'info',
  Paid: 'success',
};

export function InvoiceTable({ rows = [], onSelect }) {
  return (
    <table className="data-table invoice-table">
      <thead>
        <tr>
          <th>Invoice</th>
          <th>Customer</th>
          <th>Subscription</th>
          <th>Date</th>
          <th>Due</th>
          <th className="amount-column">Total</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>
              <button className="table-link" type="button" onClick={() => onSelect?.(row)}>
                {row.invoiceNumber}
              </button>
            </td>
            <td>{row.customer}</td>
            <td>{row.subscription}</td>
            <td>{row.date}</td>
            <td>{row.due}</td>
            <td className="amount-column">{currency.format(row.total)}</td>
            <td>
              <span className={`status-pill ${statusClass[row.status]}`}>
                <span className="dot" />
                {row.status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
