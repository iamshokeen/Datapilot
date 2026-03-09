import { useState } from 'react';
import { ArrowUpDown, Table as TableIcon } from 'lucide-react';

export default function DataTable({ data }) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  if (!data || data.length === 0) {
    return (
      <div className="border border-gray-700 rounded-lg p-8 text-center">
        <TableIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-400">No data to display</p>
      </div>
    );
  }

  const columns = Object.keys(data[0]);

  const sortedData = [...data].sort((a, b) => {
    if (!sortConfig.key) return 0;

    const aVal = a[sortConfig.key];
    const bVal = b[sortConfig.key];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
    }

    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();

    if (sortConfig.direction === 'asc') {
      return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
    } else {
      return aStr > bStr ? -1 : aStr < bStr ? 1 : 0;
    }
  });

  const handleSort = (column) => {
    setSortConfig(prev => ({
      key: column,
      direction: prev.key === column && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const formatValue = (value) => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'number') {
      return value.toLocaleString();
    }
    return String(value);
  };

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-dp-dark-50">
            <tr>
              {columns.map(column => (
                <th
                  key={column}
                  onClick={() => handleSort(column)}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-dp-dark-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span>{column}</span>
                    <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {sortedData.map((row, idx) => (
              <tr key={idx} className="hover:bg-dp-dark-50 transition-colors">
                {columns.map(column => (
                  <td key={column} className="px-4 py-3 text-sm text-gray-300 whitespace-nowrap">
                    {formatValue(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="bg-dp-dark-50 px-4 py-2 border-t border-gray-700">
        <p className="text-xs text-gray-500">
          {sortedData.length} row{sortedData.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
}
