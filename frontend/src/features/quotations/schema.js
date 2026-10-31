import { z } from 'zod';

export const quotationSchema = z.object({
  reference: z.string().min(2),
  customer: z.string().min(2),
  total: z.number().min(0),
});
