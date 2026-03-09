import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, History, LogOut } from 'lucide-react';
import { askQuestion } from '../api/client';
import { getHistoryFromStorage, saveHistoryToStorage } from '../lib/utils';
import QueryProgress from './QueryProgress';
import QueryResult from './QueryResult';

export default function ChatInterface({ connectionId, alias, onDisconnect, onShowHistory, initialQuestion = '' }) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [currentResult, setCurrentResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState(() => getHistoryFromStorage());
  const inputRef = useRef(null);
  const resultsRef = useRef(null);

  const EXAMPLE_QUESTIONS = [
    "What was the total gross GMV from confirmed bookings this fiscal year?",
    "Show me occupancy rates by location for the last quarter",
    "What is the lead to booking conversion rate this month?",
    "Top 5 performing channels by booking count"
  ];

  // Handle initial question from history
  useEffect(() => {
    if (initialQuestion && !loading) {
      setQuestion(initialQuestion);
    }
  }, [initialQuestion]);

  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [loading]);

  const simulateProgress = () => {
    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step < 5) {
        setProgressStep(step);
      } else {
        clearInterval(interval);
      }
    }, 800);
    return interval;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userQuestion = question.trim();
    setQuestion('');
    setLoading(true);
    setError(null);
    setCurrentResult(null);
    setProgressStep(0);

    const progressInterval = simulateProgress();

    try {
      const response = await askQuestion({
        connection_id: connectionId,
        question: userQuestion
      });

      clearInterval(progressInterval);
      setProgressStep(5);
      setCurrentResult(response);

      // Add to history
      const newHistory = [
        { question: userQuestion, result: response, timestamp: Date.now() },
        ...history
      ].slice(0, 50);
      setHistory(newHistory);
      saveHistoryToStorage(newHistory);

      // Scroll to results
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err) {
      clearInterval(progressInterval);
      setError(err.response?.data?.detail || err.message || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (exampleQuestion) => {
    setQuestion(exampleQuestion);
    inputRef.current?.focus();
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-dp-dark-100 border-b border-gray-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-dp-accent" />
              <h1 className="text-xl font-bold text-white">DataPilot</h1>
            </div>
            <div className="h-6 w-px bg-gray-700" />
            <div className="flex items-center gap-2 px-3 py-1 bg-dp-accent/10 rounded-full border border-dp-accent/30">
              <div className="w-2 h-2 bg-dp-accent rounded-full animate-pulse" />
              <span className="text-xs font-medium text-dp-accent">{alias}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onShowHistory}
              className="btn-secondary flex items-center gap-2 py-2 px-3"
            >
              <History className="w-4 h-4" />
              <span className="hidden sm:inline">History</span>
            </button>
            <button
              onClick={onDisconnect}
              className="btn-secondary flex items-center gap-2 py-2 px-3 text-red-400 hover:text-red-300"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Disconnect</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Welcome Message */}
          {!currentResult && !loading && (
            <div className="text-center py-12">
              <Sparkles className="w-16 h-16 text-dp-accent mx-auto mb-4 opacity-50" />
              <h2 className="text-2xl font-bold text-white mb-2">
                Ask me anything about your data
              </h2>
              <p className="text-gray-400 mb-8">
                I'll generate SQL, execute queries, and provide insights
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {EXAMPLE_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleClick(q)}
                    className="text-left p-4 bg-dp-dark-100 hover:bg-dp-dark-50 border border-gray-700 hover:border-dp-accent/50 rounded-lg transition-all text-sm text-gray-300 hover:text-white"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Progress Indicator */}
          {loading && <QueryProgress currentStep={progressStep} />}

          {/* Error */}
          {error && (
            <div className="card bg-red-500/10 border-red-500/50">
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {/* Results */}
          <div ref={resultsRef}>
            {currentResult && <QueryResult result={currentResult} />}
          </div>
        </div>
      </main>

      {/* Input Bar - Fixed at Bottom */}
      <div className="bg-dp-dark-100 border-t border-gray-800 px-6 py-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              ref={inputRef}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your data..."
              className="flex-1 input-field"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="btn-primary px-6 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Ask
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
