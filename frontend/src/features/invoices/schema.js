import { z } from 'zod';

export const invoiceSchema = z.object({
  invoiceNumber: z.string().min(2),
  customer: z.string().min(2),
  amount: z.number().min(0),
  status: z.enum(['Draft', 'Pending', 'Paid', 'Cancelled']).default('Draft'),
});
