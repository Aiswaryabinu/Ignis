import { z } from 'zod';

export const productSchema = z.object({
  name: z.string().min(2),
  category: z.string().min(2),
  status: z.enum(['Active', 'Draft', 'Archived']).default('Draft'),
});
