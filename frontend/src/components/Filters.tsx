import { useEffect, useState } from "react";
import { searchAPI } from "../utils/api";
import type { SearchFilters, CategoriesResponse } from "../types";

interface FiltersProps {
  onFilterChange: (filters: SearchFilters) => void;
  filters: SearchFilters;
}

export default function Filters({ onFilterChange, filters }: FiltersProps) {
  const [categories, setCategories] = useState<CategoriesResponse | null>(null);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const data = await searchAPI.categories();
        setCategories(data);
      } catch (err) {
        console.error("Failed to load categories:", err);
      }
    };
    loadCategories();
  }, []);

  const handleChange = (
    key: keyof SearchFilters,
    value: string | boolean | undefined
  ) => {
    const newFilters = { ...filters };

    if (value === "" || value === undefined) {
      delete newFilters[key];
    } else {
      newFilters[key] = value as any;
    }

    onFilterChange(newFilters);
  };

  if (!categories) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      {/* Visa Type Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Visa Type
        </label>
        <select
          value={filters.visa_type || ""}
          onChange={(e) => handleChange("visa_type", e.target.value)}
          className="input-field text-sm"
        >
          <option value="">All Types</option>
          {categories.visa_types.map((type) => (
            <option key={type} value={type}>
              {type.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      {/* Category Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Category
        </label>
        <select
          value={filters.primary_category || ""}
          onChange={(e) => handleChange("primary_category", e.target.value)}
          className="input-field text-sm"
        >
          <option value="">All Categories</option>
          {categories.categories.map((category) => (
            <option key={category} value={category}>
              {category
                .replace(/_/g, " ")
                .replace(/\b\w/g, (l) => l.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      {/* Location Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Location
        </label>
        <select
          value={filters.location || ""}
          onChange={(e) => handleChange("location", e.target.value)}
          className="input-field text-sm"
        >
          <option value="">All Locations</option>
          {categories.locations.map((location) => (
            <option key={location} value={location}>
              {location.charAt(0).toUpperCase() + location.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Questions Only Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Content Type
        </label>
        <select
          value={
            filters.is_question === undefined
              ? ""
              : filters.is_question
              ? "true"
              : "false"
          }
          onChange={(e) => {
            const value = e.target.value;
            handleChange(
              "is_question",
              value === "" ? undefined : value === "true"
            );
          }}
          className="input-field text-sm"
        >
          <option value="">All Content</option>
          <option value="true">Questions Only</option>
          <option value="false">Answers/Info</option>
        </select>
      </div>

      {/* Clear Filters Button */}
      <div className="md:col-span-4">
        <button
          onClick={() => onFilterChange({})}
          className="btn-secondary text-sm w-full md:w-auto"
        >
          Clear All Filters
        </button>
      </div>
    </div>
  );
}








