import { AlertCircle, Clock, FileText } from "lucide-react";
import type { SearchResult } from "../types";

interface SearchResultsProps {
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  query: string;
  processingTime: number;
}

export default function SearchResults({
  results,
  loading,
  error,
  query,
  processingTime,
}: SearchResultsProps) {
  if (loading) {
    return (
      <div className="card text-center py-12">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-3/4 mx-auto mb-4"></div>
          <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-1/2 mx-auto"></div>
        </div>
        <p className="mt-4 text-gray-600 dark:text-gray-400">Searching...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
        <div className="flex items-center space-x-3 text-red-800 dark:text-red-200">
          <AlertCircle className="w-6 h-6" />
          <div>
            <h3 className="font-semibold">Search Failed</h3>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (results.length === 0 && query) {
    return (
      <div className="card text-center py-12">
        <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
          No Results Found
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Try a different search query or adjust your filters
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Results Header */}
      <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
        <div>
          Found <span className="font-semibold">{results.length}</span> results
          for "<span className="font-semibold">{query}</span>"
        </div>
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4" />
          <span>{processingTime}ms</span>
        </div>
      </div>

      {/* Results List */}
      {results.map((result) => (
        <div
          key={result.id}
          className="card hover:shadow-lg transition-shadow duration-200"
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span
                className={`badge ${
                  result.score > 0.9
                    ? "badge-success"
                    : result.score > 0.7
                    ? "badge-primary"
                    : "badge-warning"
                }`}
              >
                {(result.score * 100).toFixed(1)}% match
              </span>
              {result.metadata.visa_type !== "unknown" && (
                <span className="badge badge-info">
                  {result.metadata.visa_type.toUpperCase()}
                </span>
              )}
              {result.metadata.is_question && (
                <span className="badge bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                  Question
                </span>
              )}
            </div>
          </div>

          <p className="text-gray-900 dark:text-gray-100 text-lg mb-3">
            {result.text}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600 dark:text-gray-400">
            <div>
              <span className="font-medium">Category:</span>{" "}
              {result.metadata.primary_category.replace(/_/g, " ")}
            </div>
            {result.metadata.location !== "unknown" && (
              <div>
                <span className="font-medium">Location:</span>{" "}
                {result.metadata.location}
              </div>
            )}
            <div>
              <span className="font-medium">Date:</span>{" "}
              {new Date(result.metadata.timestamp).toLocaleDateString()}
            </div>
            <div>
              <span className="font-medium">Length:</span>{" "}
              {result.metadata.text_length} chars
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}





