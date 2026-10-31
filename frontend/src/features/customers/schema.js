import { z } from 'zod';

export const customerSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
  status: z.enum(['Active', 'Pending', 'Inactive']).default('Active'),
});
