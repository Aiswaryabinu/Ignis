import { z } from 'zod';

export const subscriptionSchema = z.object({
  customerId: z.string().min(1),
  planId: z.string().min(1),
  status: z.enum(['Draft', 'Active', 'Cancelled']).default('Draft'),
});
