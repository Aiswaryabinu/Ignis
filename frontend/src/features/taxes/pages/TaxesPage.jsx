import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient.js';

export function TaxesPage() {
  const { data = [], isLoading, isError } = useQuery({
    queryKey: ['taxes'],
    queryFn: async () => (await apiClient.get('/taxes')).data,
  });

  return (
    <AppShell title="Taxes" description="Rules used to calculate invoice taxes." breadcrumb="Brightloop / Taxes" activeNav="taxes">
      <div className="data-card">
        <table className="data-table">
          <thead><tr><th>Name</th><th>Rate</th><th>Type</th><th>Applies to</th><th>Status</th></tr></thead>
          <tbody>
            {isLoading && <tr><td colSpan="5">Loading taxes…</td></tr>}
            {isError && <tr><td colSpan="5">Unable to load taxes.</td></tr>}
            {!isLoading && !isError && data.map((tax) => (
              <tr key={tax.id}>
                <td>{tax.name}</td><td>{tax.rate}</td><td>{tax.type}</td><td>{tax.applies}</td><td>{tax.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="table-footer">Showing {data.length} records</div>
      </div>
    </AppShell>
  );
}
