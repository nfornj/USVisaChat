import { MessageSquare, Database } from "lucide-react";
import type { StatsResponse } from "../types";

interface HeaderProps {
  stats: StatsResponse | null;
}

export default function Header({ stats }: HeaderProps) {
  return (
    <header className="bg-white dark:bg-gray-800 shadow-md border-b border-gray-200 dark:border-gray-700">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="bg-primary-600 p-3 rounded-lg">
              <MessageSquare className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Visa Search
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Search through{" "}
                {stats ? stats.total_vectors.toLocaleString() : "1.5M+"} visa
                conversations
              </p>
            </div>
          </div>

          {stats && (
            <div className="hidden md:flex items-center space-x-4">
              <div className="flex items-center space-x-2 bg-green-50 dark:bg-green-900/20 px-4 py-2 rounded-lg">
                <Database className="w-5 h-5 text-green-600 dark:text-green-400" />
                <div>
                  <div className="text-sm font-semibold text-green-900 dark:text-green-100">
                    {stats.status === "green" ? "Online" : "Offline"}
                  </div>
                  <div className="text-xs text-green-600 dark:text-green-400">
                    {stats.embedding_model.split("/").pop()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}








