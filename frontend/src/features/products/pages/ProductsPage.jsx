import { AppShell } from '../../../components/layout/AppShell.jsx';

const products = [
  {
    name: 'CloudDesk Pro',
    type: 'Software',
    sales: '₹7,500',
    cost: '₹3,100',
    variants: 'Brand: Odoo (+₹560)',
    status: 'Active',
  },
  {
    name: 'Analytics Suite',
    type: 'Software',
    sales: '₹21,600',
    cost: '₹9,800',
    variants: 'Edition: Plus (+₹1,200)',
    status: 'Active',
  },
  {
    name: 'SecureVault',
    type: 'Add-on',
    sales: '₹1,400',
    cost: '₹520',
    variants: 'None',
    status: 'Active',
  },
];

export function ProductsPage() {
  return (
    <AppShell
      title="Products"
      description="What you sell, with cost, price and variants."
      breadcrumb="Brightloop / Products"
      activeNav="products"
      primaryAction={<button className="primary-action">+ Create</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <div className="table-toolbar">
        <div className="search-box">Search products...</div>
        <div className="filter-select">All statuses ⌄</div>
      </div>

      <div className="data-card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Type</th>
              <th>Sales price</th>
              <th>Cost price</th>
              <th>Variants</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.name}>
                <td className="product-name">{product.name}</td>
                <td>{product.type}</td>
                <td>{product.sales}</td>
                <td>{product.cost}</td>
                <td>{product.variants}</td>
                <td>
                  <span className={`status-pill ${product.status === 'Active' ? 'success' : 'muted'}`}>
                    <span className="dot" />
                    {product.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="table-footer">Showing 3 of 3 records</div>
      </div>
    </AppShell>
  );
}
