import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table';
import { Fragment, useState } from 'react';
import type { ResultCandidate } from '../types/ga';

const columnHelper = createColumnHelper<ResultCandidate>();

const columns = [
  columnHelper.accessor('rank', { header: 'Rank' }),
  columnHelper.accessor('fitness', { header: 'Fitness' }),
  columnHelper.accessor('profit', { header: 'Profit %' }),
  columnHelper.accessor('sharpe', { header: 'Sharpe' }),
  columnHelper.accessor('drawdown', { header: 'Drawdown %' }),
];

export default function ResultsTable({ results }: { results: ResultCandidate[] }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'rank', desc: false }]);
  const [expandedRank, setExpandedRank] = useState<number | null>(null);
  const table = useReactTable({
    data: results,
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
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => (
                <th key={header.id}>
                  <button type="button" onClick={header.column.getToggleSortingHandler()}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </button>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <Fragment key={row.id}>
              <tr onClick={() => setExpandedRank(row.original.rank)}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
              {expandedRank === row.original.rank ? (
                <tr key={`${row.id}-detail`}>
                  <td colSpan={columns.length}>
                    <pre>{JSON.stringify(row.original.parameters, null, 2)}</pre>
                  </td>
                </tr>
              ) : null}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
