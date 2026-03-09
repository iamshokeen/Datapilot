import { ArrowLeft, Clock, Trash2 } from 'lucide-react';
import { getHistoryFromStorage, saveHistoryToStorage, formatDuration } from '../lib/utils';
import { useState } from 'react';

export default function HistoryView({ onBack, onSelectQuestion }) {
  const [history, setHistory] = useState(() => getHistoryFromStorage());

  const handleClear = () => {
    if (confirm('Are you sure you want to clear all history?')) {
      setHistory([]);
      saveHistoryToStorage([]);
    }
  };

  const handleReRun = (item) => {
    onSelectQuestion(item.question);
    onBack();
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="min-h-screen bg-dp-dark-200 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={onBack}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Chat
          </button>

          {history.length > 0 && (
            <button
              onClick={handleClear}
              className="btn-secondary flex items-center gap-2 text-red-400 hover:text-red-300"
            >
              <Trash2 className="w-4 h-4" />
              Clear History
            </button>
          )}
        </div>

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">Query History</h1>
          <p className="text-gray-400">
            {history.length} quer{history.length !== 1 ? 'ies' : 'y'} in session
          </p>
        </div>

        {/* History List */}
        {history.length === 0 ? (
          <div className="card text-center py-12">
            <Clock className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No queries yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((item, idx) => (
              <button
                key={idx}
                onClick={() => handleReRun(item)}
                className="w-full card hover:border-dp-accent/50 transition-all text-left group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white mb-2 group-hover:text-dp-accent transition-colors">
                      {item.question}
                    </p>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                      <span>{formatTimestamp(item.timestamp)}</span>
                      <span>•</span>
                      <span>{item.result.total_rows} rows</span>
                      <span>•</span>
                      <span>{formatDuration(item.result.processing_time_ms)}</span>
                      {item.result.sub_question_count > 1 && (
                        <>
                          <span>•</span>
                          <span>{item.result.sub_question_count} sub-questions</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 group-hover:text-dp-accent transition-colors">
                    Click to re-run
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
