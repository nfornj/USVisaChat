import { Database, Cpu, Hash, Activity } from "lucide-react";
import type { StatsResponse } from "../types";

interface StatsProps {
  stats: StatsResponse;
}

export default function Stats({ stats }: StatsProps) {
  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">
        Database Statistics
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="flex items-start space-x-4">
          <div className="bg-primary-100 dark:bg-primary-900 p-3 rounded-lg">
            <Database className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Total Vectors
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.total_vectors.toLocaleString()}
            </div>
          </div>
        </div>

        <div className="flex items-start space-x-4">
          <div className="bg-green-100 dark:bg-green-900 p-3 rounded-lg">
            <Activity className="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Status
            </div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {stats.status}
            </div>
          </div>
        </div>

        <div className="flex items-start space-x-4">
          <div className="bg-blue-100 dark:bg-blue-900 p-3 rounded-lg">
            <Hash className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Dimensions
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.vector_dimensions}
            </div>
          </div>
        </div>

        <div className="flex items-start space-x-4">
          <div className="bg-purple-100 dark:bg-purple-900 p-3 rounded-lg">
            <Cpu className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Model
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-white">
              {stats.embedding_model.split("/").pop()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}








