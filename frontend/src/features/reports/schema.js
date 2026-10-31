import { z } from 'zod';

export const reportSchema = z.object({
  type: z.enum(['Revenue', 'Customers', 'Invoices', 'Subscriptions']),
  period: z.enum(['7d', '30d', '90d']).default('30d'),
});
