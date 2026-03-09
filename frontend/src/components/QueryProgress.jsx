import { Loader2, CheckCircle2 } from 'lucide-react';

const STEPS = [
  { id: 'planning', label: 'Planning query' },
  { id: 'generating', label: 'Generating SQL' },
  { id: 'executing', label: 'Executing query' },
  { id: 'analyzing', label: 'Analyzing results' },
  { id: 'summarizing', label: 'Writing summary' }
];

export default function QueryProgress({ currentStep = 0 }) {
  return (
    <div className="card">
      <div className="space-y-3">
        {STEPS.map((step, index) => {
          const isActive = index === currentStep;
          const isComplete = index < currentStep;

          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 transition-all duration-300 ${
                isActive ? 'opacity-100' : isComplete ? 'opacity-60' : 'opacity-30'
              }`}
            >
              <div className="flex-shrink-0">
                {isComplete ? (
                  <CheckCircle2 className="w-5 h-5 text-dp-accent" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 text-dp-accent animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-600" />
                )}
              </div>
              <span
                className={`text-sm font-medium ${
                  isActive ? 'text-white' : isComplete ? 'text-gray-400' : 'text-gray-600'
                }`}
              >
                {step.label}
                {isActive && '...'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
