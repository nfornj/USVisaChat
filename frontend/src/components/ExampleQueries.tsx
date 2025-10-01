import { useEffect, useState } from "react";
import { Lightbulb } from "lucide-react";
import { searchAPI } from "../utils/api";
import type { SearchExample } from "../types";

interface ExampleQueriesProps {
  onExampleClick: (query: string) => void;
}

export default function ExampleQueries({
  onExampleClick,
}: ExampleQueriesProps) {
  const [examples, setExamples] = useState<SearchExample[]>([]);

  useEffect(() => {
    const loadExamples = async () => {
      try {
        const data = await searchAPI.examples();
        setExamples(data.examples);
      } catch (err) {
        console.error("Failed to load examples:", err);
      }
    };
    loadExamples();
  }, []);

  if (examples.length === 0) return null;

  return (
    <div className="card">
      <div className="flex items-center space-x-2 mb-4">
        <Lightbulb className="w-6 h-6 text-yellow-500" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
          Try These Example Searches
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {examples.map((example, index) => (
          <button
            key={index}
            onClick={() => onExampleClick(example.query)}
            className="text-left p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all group"
          >
            <div className="font-medium text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 mb-1">
              "{example.query}"
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {example.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}





