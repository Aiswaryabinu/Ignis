import { z } from 'zod';

export const paymentSchema = z.object({
  reference: z.string().min(2),
  method: z.enum(['UPI', 'Card', 'Bank Transfer', 'Cash']),
  status: z.enum(['Pending', 'Paid', 'Failed']).default('Pending'),
});
