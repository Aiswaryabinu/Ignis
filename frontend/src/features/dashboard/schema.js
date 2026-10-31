import { z } from 'zod';

export const dashboardFiltersSchema = z.object({
  period: z.enum(['30d', '90d', '1y']).default('30d'),
});
