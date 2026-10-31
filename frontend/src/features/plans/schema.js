import { z } from 'zod';

export const planSchema = z.object({
  name: z.string().min(2),
  price: z.number().min(0),
  billingCycle: z.enum(['Monthly', 'Quarterly', 'Yearly']),
});
