import { useState, useMemo, useCallback, useRef, useEffect, type ReactNode } from "react";
import { LoadingSpinner } from "./LoadingSpinner";

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (row: T) => ReactNode;
}

interface FilterableTableProps<T> {
  columns: Column<T>[];
  data: T[];
  total: number;
  isLoading?: boolean;
  error?: string | null;
  onSearch?: (query: string) => void;
  filters?: ReactNode;
  exportFileName?: string;
  pageSize?: number;
}

type SortDir = "asc" | "desc" | null;

function CSV_escape(value: unknown): string {
  const str = String(value ?? "");
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function array_to_csv<T>(data: T[], columns: Column<T>[]): string {
  const header = columns.map((c) => CSV_escape(c.label)).join(",");
  const rows = data.map((row) =>
    columns.map((c) => CSV_escape((row as Record<string, unknown>)[c.key])).join(","),
  );
  return [header, ...rows].join("\n");
}

export function FilterableTable<T extends Record<string, unknown>>({
  columns,
  data,
  total,
  isLoading = false,
  error = null,
  onSearch,
  filters,
  exportFileName = "export.csv",
  pageSize = 25,
}: FilterableTableProps<T>) {
  const [search, set_search] = useState("");
  const [page, set_page] = useState(0);
  const [sort_key, set_sort_key] = useState<string | null>(null);
  const [sort_dir, set_sort_dir] = useState<SortDir>(null);
  const debounce_ref = useRef<ReturnType<typeof setTimeout>>();

  const total_pages = Math.max(1, Math.ceil(total / pageSize));
  const from = page * pageSize + 1;
  const to = Math.min((page + 1) * pageSize, total);

  useEffect(() => {
    set_page(0);
  }, [search]);

  const handle_search = useCallback(
    (value: string) => {
      set_search(value);
      clearTimeout(debounce_ref.current);
      debounce_ref.current = setTimeout(() => {
        onSearch?.(value);
      }, 300);
    },
    [onSearch],
  );

  const handle_sort = useCallback(
    (key: string) => {
      if (sort_key === key) {
        if (sort_dir === "asc") {
          set_sort_dir("desc");
        } else if (sort_dir === "desc") {
          set_sort_key(null);
          set_sort_dir(null);
        }
      } else {
        set_sort_key(key);
        set_sort_dir("asc");
      }
    },
    [sort_key, sort_dir],
  );

  const sorted_data = useMemo(() => {
    if (!sort_key || !sort_dir) return data;
    return [...data].sort((a, b) => {
      const a_val = a[sort_key];
      const b_val = b[sort_key];
      if (a_val == null) return 1;
      if (b_val == null) return -1;
      const cmp = typeof a_val === "number" ? a_val - (b_val as number) : String(a_val).localeCompare(String(b_val));
      return sort_dir === "asc" ? cmp : -cmp;
    });
  }, [data, sort_key, sort_dir]);

  const handle_export = useCallback(() => {
    const csv = array_to_csv(data, columns);
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = exportFileName;
    a.click();
    URL.revokeObjectURL(url);
  }, [data, columns, exportFileName]);

  return (
    <div className="space-y-4">
      {/* Search + Filters + Export */}
      <div className="flex flex-wrap items-center gap-3">
        {onSearch && (
          <div className="relative min-w-[200px] flex-1">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => handle_search(e.target.value)}
              placeholder="Buscar..."
              className="block w-full rounded-md border border-gray-300 py-2 pl-10 pr-3 text-sm shadow-sm transition-colors placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
            />
          </div>
        )}
        {filters}
        <button
          type="button"
          onClick={handle_export}
          className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
        >
          <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Exportar CSV
        </button>
      </div>

      {/* Table */}
      {error && (
        <div className="flex items-center gap-3 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <svg className="h-5 w-5 flex-shrink-0 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="h-8 w-8" />
        </div>
      ) : !error && data.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-gray-400">
          <svg className="mb-2 h-12 w-12" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
          </svg>
          <p className="text-sm">No se encontraron resultados</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 ${
                      col.sortable ? "cursor-pointer select-none hover:bg-gray-100" : ""
                    }`}
                    onClick={() => col.sortable && handle_sort(col.key)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.sortable && sort_key === col.key && (
                        <svg className="h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          {sort_dir === "asc" ? (
                            <path fillRule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.97-3.97a.75.75 0 111.06 1.06l-5.25 5.25a.75.75 0 01-1.06 0l-5.25-5.25a.75.75 0 011.06-1.06l3.97 3.97V3.75A.75.75 0 0110 3z" clipRule="evenodd" />
                          ) : (
                            <path fillRule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612l-3.97 3.97a.75.75 0 11-1.06-1.06l5.25-5.25a.75.75 0 011.06 0l5.25 5.25a.75.75 0 01-1.06 1.06L10.75 5.612V16.25A.75.75 0 0110 17z" clipRule="evenodd" />
                          )}
                        </svg>
                      )}
                      {col.sortable && sort_key !== col.key && (
                        <svg className="h-3 w-3 text-gray-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          <path d="M10 3a.75.75 0 01.75.75v10.638l1.97-1.97a.75.75 0 111.06 1.06l-3.25 3.25a.75.75 0 01-1.06 0l-3.25-3.25a.75.75 0 111.06-1.06l1.97 1.97V3.75A.75.75 0 0110 3z" />
                        </svg>
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sorted_data.map((row, i) => (
                <tr key={(row.id as string) ?? i} className="hover:bg-gray-50">
                  {columns.map((col) => (
                    <td key={col.key} className="whitespace-nowrap px-4 py-3 text-gray-700">
                      {col.render ? col.render(row) : (row[col.key] as ReactNode) ?? "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > pageSize && !isLoading && !error && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <p>
            {from}–{to} de {total}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => set_page((p) => Math.max(0, p - 1))}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:text-gray-400 disabled:hover:bg-white"
            >
              <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clipRule="evenodd" />
              </svg>
              Anterior
            </button>
            <span className="text-xs text-gray-400">
              {page + 1} de {total_pages}
            </span>
            <button
              type="button"
              disabled={page >= total_pages - 1}
              onClick={() => set_page((p) => Math.min(total_pages - 1, p + 1))}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:text-gray-400 disabled:hover:bg-white"
            >
              Siguiente
              <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
