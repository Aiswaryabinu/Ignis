import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../lib/apiClient';

export function useInvoices() {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const response = await apiClient.get('/invoices');
      return response.data;
    },
  });
}
