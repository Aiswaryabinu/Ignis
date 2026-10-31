import { z } from 'zod';

export const settingsSchema = z.object({
  role: z.enum(['Admin', 'Staff', 'Customer']),
  status: z.enum(['Active', 'Inactive']).default('Active'),
});
