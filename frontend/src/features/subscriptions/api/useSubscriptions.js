import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../lib/apiClient';

export function useSubscriptions() {
  return useQuery({
    queryKey: ['subscriptions'],
    queryFn: async () => {
      const response = await apiClient.get('/subscriptions');
      return response.data;
    },
  });
}
