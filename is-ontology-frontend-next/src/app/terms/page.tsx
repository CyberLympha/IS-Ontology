"use client"

import { getTerms } from "@/api"
import { Term } from "@/api/types"
import Box from "@mui/material/Box"
import Paper from "@mui/material/Paper"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TableSortLabel from "@mui/material/TableSortLabel"
import Typography from "@mui/material/Typography"
import { RankingInfo, compareItems, rankItem } from "@tanstack/match-sorter-utils"
import { Column, SortingState, createColumnHelper, flexRender, getCoreRowModel, getSortedRowModel, useReactTable, Table as TanTable, ColumnFiltersState, getFilteredRowModel, FilterFn, SortingFn, sortingFns } from "@tanstack/react-table"
import { useEffect, useMemo, useState } from "react"
declare module '@tanstack/table-core' {
    interface FilterFns {
        fuzzy: FilterFn<unknown>
    }
    interface FilterMeta {
        itemRank: RankingInfo
    }
}

export default function Page() {
    const [terms, setTerms] = useState<Term[]>([])
    useEffect(() => {
        getTerms().then(r => {
            setTerms(r.data.terms)
        })
    }, [])

    const columnHelper = createColumnHelper<Term>()
    const valueToHeader = useMemo(() => {
        return {
            "term": "Термин",
            "doc.desc": "Документ",
            "expert": "Эксперт",
            "date": "Дата добавления"
        } as Record<string, string>
    }, [])

    const columns = useMemo(() => ["term", "doc.desc", "expert", "date"].map(v =>
        columnHelper.accessor(v as unknown as any, {
            cell: r => v == "date" ? new Date(r.getValue()).toLocaleDateString(undefined, { dateStyle: "short" }) : r.getValue(),
            header: valueToHeader[v],
            filterFn: 'auto'
        })), [columnHelper, valueToHeader])

    const [sorting, setSorting] = useState<SortingState>([])
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>(
        []
    )

    const table = useReactTable({
        data: terms,
        columns: columns,
        getCoreRowModel: getCoreRowModel(),
        state: {
            sorting,
            columnFilters
        },
        filterFns: {
            fuzzy: fuzzyFilter
        },
        onSortingChange: setSorting,
        getSortedRowModel: getSortedRowModel(),
        onColumnFiltersChange: setColumnFilters,
        getFilteredRowModel: getFilteredRowModel()
    })

    return <Box>
        <Typography variant='h1'>Список терминов информационной безопасности</Typography>
        <TableContainer component={Paper}>
            <Table size="small">
                <TableHead>
                    {table.getHeaderGroups().map(headerGroup => <TableRow key={headerGroup.id}>{headerGroup.headers.map(header => <TableCell key={header.id}>
                        <TableSortLabel onClick={header.column.getToggleSortingHandler()} active={!!header.column.getIsSorted()} direction={(header.column.getIsSorted() || "asc") as any}>
                            {flexRender(header.column.columnDef.header, header.getContext())}{/*{
                                asc: ' 🔼',
                                desc: ' 🔽',
                            }[header.column.getIsSorted() as string] ?? null*/}
                        </TableSortLabel>
                        {header.column.getCanFilter() ? <div>
                            <Filter column={header.column} table={table} />
                        </div> : null}
                    </TableCell>
                    )}</TableRow>)}
                </TableHead>
                <TableBody>
                    {table.getRowModel().rows.map(row =>
                        <TableRow key={row.id}>
                            {row.getVisibleCells().map(c => <TableCell key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</TableCell>)}
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </TableContainer>
    </Box>
}

// refactor

const fuzzyFilter: FilterFn<any> = (row, columnId, value, addMeta) => {
    // Rank the item
    const itemRank = rankItem(row.getValue(columnId), value)

    // Store the itemRank info
    addMeta({
        itemRank,
    })

    // Return if the item should be filtered in/out
    return itemRank.passed
}


const fuzzySort: SortingFn<any> = (rowA, rowB, columnId) => {
    let dir = 0

    // Only sort by rank if the column has ranking information
    if (rowA.columnFiltersMeta[columnId]) {
        dir = compareItems(
            rowA.columnFiltersMeta[columnId]?.itemRank!,
            rowB.columnFiltersMeta[columnId]?.itemRank!
        )
    }

    // Provide an alphanumeric fallback for when the item ranks are equal
    return dir === 0 ? sortingFns.alphanumeric(rowA, rowB, columnId) : dir
}

function Filter({
    column,
    table,
}: {
    column: Column<any, unknown>
    table: TanTable<any>
}) {
    const firstValue = table
        .getPreFilteredRowModel()
        .flatRows[0]?.getValue(column.id)

    const columnFilterValue = column.getFilterValue()

    const sortedUniqueValues = useMemo(
        () =>
            typeof firstValue === 'number'
                ? []
                : Array.from(column.getFacetedUniqueValues().keys()).sort(),
        [column.getFacetedUniqueValues()]
    )

    return typeof firstValue === 'number' ? (
        <div>
            <div className="flex space-x-2">
                <DebouncedInput
                    type="number"
                    min={Number(column.getFacetedMinMaxValues()?.[0] ?? '')}
                    max={Number(column.getFacetedMinMaxValues()?.[1] ?? '')}
                    value={(columnFilterValue as [number, number])?.[0] ?? ''}
                    onChange={value =>
                        column.setFilterValue((old: [number, number]) => [value, old?.[1]])
                    }
                    placeholder={`Min ${column.getFacetedMinMaxValues()?.[0]
                        ? `(${column.getFacetedMinMaxValues()?.[0]})`
                        : ''
                        }`}
                    className="w-24 border shadow rounded"
                />
                <DebouncedInput
                    type="number"
                    min={Number(column.getFacetedMinMaxValues()?.[0] ?? '')}
                    max={Number(column.getFacetedMinMaxValues()?.[1] ?? '')}
                    value={(columnFilterValue as [number, number])?.[1] ?? ''}
                    onChange={value =>
                        column.setFilterValue((old: [number, number]) => [old?.[0], value])
                    }
                    placeholder={`Max ${column.getFacetedMinMaxValues()?.[1]
                        ? `(${column.getFacetedMinMaxValues()?.[1]})`
                        : ''
                        }`}
                    className="w-24 border shadow rounded"
                />
            </div>
            <div className="h-1" />
        </div>
    ) : (
        <>
            <datalist id={column.id + 'list'}>
                {sortedUniqueValues.slice(0, 5000).map((value: any) => (
                    <option value={value} key={value} />
                ))}
            </datalist>
            <DebouncedInput
                type="text"
                value={(columnFilterValue ?? '') as string}
                onChange={value => column.setFilterValue(value)}
                // placeholder={`Search... (${column.getFacetedUniqueValues().size})`}
                className="w-36 border shadow rounded"
                list={column.id + 'list'}
            />
            <div className="h-1" />
        </>
    )
}

// A debounced input react component
function DebouncedInput({
    value: initialValue,
    onChange,
    debounce = 500,
    ...props
}: {
    value: string | number
    onChange: (value: string | number) => void
    debounce?: number
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'>) {
    const [value, setValue] = useState(initialValue)

    useEffect(() => {
        setValue(initialValue)
    }, [initialValue])

    useEffect(() => {
        const timeout = setTimeout(() => {
            onChange(value)
        }, debounce)

        return () => clearTimeout(timeout)
    }, [value])

    return (
        <input {...props} value={value} onChange={e => setValue(e.target.value)} />
    )
}

