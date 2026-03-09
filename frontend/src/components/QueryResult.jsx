import { Clock, Layers, TrendingUp, AlertCircle } from 'lucide-react';
import { formatDuration } from '../lib/utils';
import SQLDisplay from './SQLDisplay';
import DataTable from './DataTable';

export default function QueryResult({ result }) {
  if (!result) return null;

  const mainResult = result.results?.[0];
  const sql = mainResult?.sql;

  return (
    <div className="space-y-4">
      {/* Narrative - Most Prominent */}
      <div className="card">
        <div className="prose prose-invert max-w-none">
          <p className="text-lg text-gray-200 leading-relaxed mb-0">
            {result.narrative}
          </p>
        </div>
      </div>

      {/* Sub-questions if query was decomposed */}
      {result.sub_questions && result.sub_questions.length > 1 && (
        <div className="card">
          <div className="flex items-start gap-2 mb-3">
            <Layers className="w-5 h-5 text-dp-accent mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-white">Query Decomposition</h3>
              <p className="text-xs text-gray-400 mt-1">
                Complex question broken into {result.sub_questions.length} parts
              </p>
            </div>
          </div>
          <ul className="space-y-2 ml-7">
            {result.sub_questions.map((sq, idx) => (
              <li key={idx} className="text-sm text-gray-300">
                {idx + 1}. {sq}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Chart Suggestion */}
      {result.chart_suggestion && result.chart_suggestion.type !== 'table' && (
        <div className="card bg-dp-accent/5 border-dp-accent/20">
          <div className="flex items-start gap-2">
            <TrendingUp className="w-5 h-5 text-dp-accent mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-white">Chart Recommendation</h3>
              <p className="text-sm text-gray-300 mt-1">
                <span className="font-medium text-dp-accent">{result.chart_suggestion.type}</span>
                {' — '}
                {result.chart_suggestion.reason}
              </p>
              {result.chart_suggestion.x_axis && (
                <p className="text-xs text-gray-400 mt-1">
                  X: {result.chart_suggestion.x_axis} • Y: {result.chart_suggestion.y_axis}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SQL Code */}
      {sql && <SQLDisplay sql={sql} />}

      {/* Data Table */}
      {result.data && result.data.length > 0 && (
        <DataTable data={result.data} />
      )}

      {/* Metadata Footer */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          <span>{formatDuration(result.processing_time_ms)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5" />
          <span>{result.total_rows} rows returned</span>
        </div>
        {result.results?.some(r => r.retries > 0) && (
          <div className="flex items-center gap-1.5 text-yellow-500">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{result.results[0].retries} SQL retries</span>
          </div>
        )}
      </div>
    </div>
  );
}
