import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../lib/apiClient';

export function useCustomers() {
  return useQuery({
    queryKey: ['customers'],
    queryFn: async () => {
      const response = await apiClient.get('/customers');
      return response.data;
    },
  });
}
