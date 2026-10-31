import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';
import { downloadCsv } from '../../../lib/exportCsv.js';

const staff = [
  { name: 'Aisha Khan', email: 'aisha@brightloop.in', role: 'Admin', status: 'Active' },
  { name: 'Rohan Mehta', email: 'rohan@brightloop.in', role: 'Staff', status: 'Active' },
  { name: 'Divya Nair', email: 'divya@brightloop.in', role: 'Staff', status: 'Active' },
];

export function SettingsPage() {
  const [query, setQuery] = useState('');
  const [isOpen, setOpen] = useState(false);
  const visibleStaff = useMemo(() => staff.filter((person) => `${person.name} ${person.email}`.toLowerCase().includes(query.toLowerCase())), [query]);
  const exportStaff = () => downloadCsv('staff-users.csv', visibleStaff);

  return (
    <AppShell title="Staff & Users" description="Team access. Only admins can add staff." breadcrumb="Brightloop / Staff & Users" activeNav="staff-users" primaryAction={<button className="primary-action" type="button" onClick={() => setOpen(true)}>+ Add staff</button>} secondaryAction={<button className="secondary-action" type="button" onClick={exportStaff}>Export</button>}>
      <div className="settings-toolbar"><input className="settings-search" type="search" placeholder="Search settings..." aria-label="Search settings" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      <div className="data-card settings-card"><table className="data-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{visibleStaff.map((person) => <tr key={person.email}><td className="table-link">{person.name}</td><td>{person.email}</td><td>{person.role}</td><td><span className="status-pill success"><span className="dot" />{person.status}</span></td></tr>)}</tbody></table><div className="table-footer">Showing {visibleStaff.length} of {staff.length} records</div></div>
      <Drawer title="Add staff" isOpen={isOpen} onClose={() => setOpen(false)} className="form-drawer"><form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setOpen(false); }}><label>Name<input required /></label><label>Email<input type="email" required /></label><button className="primary-action drawer-submit" type="submit">Save</button></form></Drawer>
    </AppShell>
  );
}
