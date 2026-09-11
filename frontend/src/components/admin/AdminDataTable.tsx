import type { ReactNode } from 'react';
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react';

export type SortDirection = 'asc' | 'desc';

export interface AdminTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  className?: string;
}

interface AdminDataTableProps<T> {
  columns: AdminTableColumn<T>[];
  rows: T[];
  getKey: (row: T) => string | number;
  sortKey?: string;
  sortDirection?: SortDirection;
  onSort?: (key: string) => void;
  emptyTitle: string;
  emptyMessage: string;
}

export function AdminDataTable<T>({
  columns,
  rows,
  getKey,
  sortKey,
  sortDirection,
  onSort,
  emptyTitle,
  emptyMessage,
}: AdminDataTableProps<T>) {
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-white/[0.025]">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.03]">
              {columns.map((column) => {
                const sortable = Boolean(column.sortValue && onSort);
                const active = sortKey === column.key;
                const ariaSort = active ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none';

                return (
                  <th
                    key={column.key}
                    aria-sort={sortable ? ariaSort : undefined}
                    className={`px-4 py-3 text-[11px] font-semibold uppercase tracking-[.12em] text-zinc-500 ${column.className ?? ''}`}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => onSort?.(column.key)}
                        className="inline-flex min-h-8 items-center gap-1.5 text-left transition hover:text-zinc-200"
                      >
                        {column.header}
                        {active ? (
                          sortDirection === 'asc' ? <ArrowUp size={13} /> : <ArrowDown size={13} />
                        ) : (
                          <ChevronsUpDown size={13} />
                        )}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center">
                  <p className="font-medium text-zinc-200">{emptyTitle}</p>
                  <p className="mt-1 text-sm text-zinc-500">{emptyMessage}</p>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={getKey(row)}
                  className="border-b border-white/5 transition last:border-0 hover:bg-white/[0.035]"
                >
                  {columns.map((column) => (
                    <td key={column.key} className={`px-4 py-3.5 align-middle ${column.className ?? ''}`}>
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
