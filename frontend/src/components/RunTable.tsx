import { useState, useEffect } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  SortingState,
} from '@tanstack/react-table';
import { format } from 'date-fns';
import { ArrowUpDown, Play, Eye } from 'lucide-react';

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Run } from '@/types/api';
import { getRuns } from '@/lib/api';
import { useToaster } from '@/components/ui/toaster';

const columns: ColumnDef<Run>[] = [
  {
    accessorKey: 'id',
    header: 'ID',
    cell: ({ row }) => <div className="font-mono">{row.getValue('id')}</div>,
  },
  {
    accessorKey: 'initial_url',
    header: 'Initial URL',
    cell: ({ row }) => (
      <div className="max-w-xs truncate" title={row.getValue('initial_url')}>
        {row.getValue('initial_url')}
      </div>
    ),
  },
  {
    accessorKey: 'started_at',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          className="text-gray-700 hover:bg-gray-100 hover:text-gray-900"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const date = new Date(row.getValue('started_at'));
      return <div>{format(date, 'MMM dd, yyyy HH:mm')}</div>;
    },
  },
  {
    accessorKey: 'result_status',
    header: 'Status',
    cell: ({ row }) => {
      const status = row.getValue('result_status') as string;
      const statusColors = {
        IN_PROGRESS: 'bg-blue-100 text-blue-800',
        SUCCESS: 'bg-green-100 text-green-800',
        FAILED: 'bg-red-100 text-red-800',
        CANCELLED: 'bg-gray-100 text-gray-800',
      };
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[status as keyof typeof statusColors] || 'bg-gray-100 text-gray-800'}`}>
          {status}
        </span>
      );
    },
  },
  {
    id: 'actions',
    header: 'Actions',
    cell: ({ row }) => {
      const run = row.original;
      return (
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            className="border-gray-300 bg-white text-gray-700 hover:bg-gray-50 hover:text-gray-900"
            onClick={() => window.open(`/run/${run.id}`, '_blank')}
          >
            <Eye className="h-4 w-4 mr-1" />
            View
          </Button>
          {run.result_status === 'IN_PROGRESS' && (
            <Button
              variant="outline"
              size="sm"
              className="border-gray-300 bg-white text-gray-700 hover:bg-gray-50 hover:text-gray-900"
              onClick={() => window.open(`/run/${run.id}/live`, '_blank')}
            >
              <Play className="h-4 w-4 mr-1" />
              Live
            </Button>
          )}
        </div>
      );
    },
  },
];

interface RunTableProps {
  refreshTrigger?: number;
}

export function RunTable({ refreshTrigger }: RunTableProps = {}) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState<SortingState>([]);
  const { addToast } = useToaster();

  const table = useReactTable({
    data: runs,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
  });

  const fetchRuns = async () => {
    try {
      const response = await getRuns();
      setRuns(response.runs);
    } catch (error) {
      console.error('Failed to fetch runs:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      if (errorMessage.includes('CONNECTION_ERROR')) {
        addToast({
          title: 'Backend Connection Error',
          description: 'Unable to connect to the backend server. Please check if the server is running.',
          variant: 'destructive',
          duration: 10000,
        });
      } else {
        addToast({
          title: 'Failed to Load Runs',
          description: errorMessage,
          variant: 'destructive',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, [addToast]);

  // Refresh runs when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger !== undefined) {
      console.log('🔄 Refreshing runs due to refresh trigger:', refreshTrigger);
      fetchRuns();
    }
  }, [refreshTrigger]);

  if (loading) {
    return <div className="flex justify-center p-8 text-gray-900">Loading runs...</div>;
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id} className="text-gray-900">
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && 'selected'}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => window.open(`/run/${row.original.id}`, '_blank')}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id} className="text-gray-900">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center text-gray-900">
                No runs found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
