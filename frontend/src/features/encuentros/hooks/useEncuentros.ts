import { useQuery } from "@tanstack/react-query";
import { fetchInstancias } from "@/features/encuentros/services/encuentros";
import type { InstanciasFilters } from "@/features/encuentros/types/encuentros";

export function useInstancias(filters?: InstanciasFilters) {
  return useQuery({
    queryKey: ["encuentros", "instancias", filters],
    queryFn: () => fetchInstancias(filters),
  });
}
