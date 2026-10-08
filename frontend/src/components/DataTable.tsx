import { useState } from 'react'
import { flexRender, getCoreRowModel, getFilteredRowModel, getSortedRowModel, useReactTable } from '@tanstack/react-table'
import type { ColumnDef, SortingState } from '@tanstack/react-table'
import { Input } from './ui/input'
export function DataTable<T>({data, columns, label}: {data: T[]; columns: ColumnDef<T>[]; label: string}) {
  const [filter, setFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  // TanStack v8 is intentionally used without React Compiler memoization.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({data, columns, state: {globalFilter: filter, sorting}, onSortingChange: setSorting, getCoreRowModel: getCoreRowModel(), getFilteredRowModel: getFilteredRowModel(), getSortedRowModel: getSortedRowModel()})
  return <><div className="table-toolbar"><Input aria-label={`Filter ${label}`} placeholder={`Search ${label}…`} value={filter} onChange={e => setFilter(e.target.value)} /><span>{table.getRowModel().rows.length} records</span></div><div className="table-scroll"><table><thead>{table.getHeaderGroups().map(group => <tr key={group.id}>{group.headers.map(header => <th key={header.id} aria-sort={header.column.getIsSorted() === 'asc' ? 'ascending' : header.column.getIsSorted() === 'desc' ? 'descending' : 'none'}><button onClick={header.column.getToggleSortingHandler()}>{flexRender(header.column.columnDef.header, header.getContext())}{header.column.getIsSorted() === 'asc' ? ' ↑' : header.column.getIsSorted() === 'desc' ? ' ↓' : ''}</button></th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map(row => <tr key={row.id}>{row.getVisibleCells().map(cell => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table>{!table.getRowModel().rows.length && <p className="empty">No matching records.</p>}</div></>
}
