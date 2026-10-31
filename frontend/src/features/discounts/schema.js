import { z } from 'zod';

export const discountSchema = z.object({
  code: z.string().min(2),
  type: z.enum(['Percentage', 'Flat']),
  value: z.number().min(0),
});
