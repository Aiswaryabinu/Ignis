export const ROLES = {
  ADMIN: 'Admin',
  STAFF: 'Staff',
  CUSTOMER: 'Customer',
};

export const permissions = {
  [ROLES.ADMIN]: ['*'],
  [ROLES.STAFF]: ['dashboard', 'customers', 'invoices', 'quotations'],
  [ROLES.CUSTOMER]: ['dashboard', 'subscriptions', 'invoices'],
};
