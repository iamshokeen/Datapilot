import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Code, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

export default function SQLDisplay({ sql }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!sql) return null;

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-dp-dark-50 hover:bg-dp-dark-100 transition-colors"
      >
        <div className="flex items-center gap-2 text-gray-300">
          <Code className="w-4 h-4" />
          <span className="text-sm font-medium">Generated SQL</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="relative">
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 p-2 bg-dp-dark-100 hover:bg-dp-dark-50 rounded-md transition-colors border border-gray-700 z-10"
            title="Copy SQL"
          >
            {copied ? (
              <Check className="w-4 h-4 text-dp-accent" />
            ) : (
              <Copy className="w-4 h-4 text-gray-400" />
            )}
          </button>
          <SyntaxHighlighter
            language="sql"
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              padding: '1rem',
              background: '#0f1114',
              fontSize: '0.875rem'
            }}
          >
            {sql}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
