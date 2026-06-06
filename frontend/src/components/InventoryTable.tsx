import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table';
import { useState } from 'react';
import type { InventoryFile } from '../types/offlineData';

const columnHelper = createColumnHelper<InventoryFile>();

const columns = [
  columnHelper.accessor('path', { header: 'Path' }),
  columnHelper.accessor('pair', { header: 'Pair', cell: (info) => info.getValue() ?? 'unknown' }),
  columnHelper.accessor('timeframe', { header: 'Timeframe', cell: (info) => info.getValue() ?? 'unknown' }),
  columnHelper.accessor('format', { header: 'Format' }),
  columnHelper.accessor('sizeBytes', {
    header: 'Size',
    cell: (info) => `${Math.round(info.getValue() / 1024)} KB`,
  }),
];

export default function InventoryTable({ files }: { files: InventoryFile[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data: files,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="table-shell">
      <table>
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id}>
                  <button type="button" onClick={header.column.getToggleSortingHandler()}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    <span>{header.column.getIsSorted() ? ` ${header.column.getIsSorted()}` : ''}</span>
                  </button>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
