// Interactive debounced search bar paired with dynamic category filter chips and match counters

"use client"

import React, { useState, useEffect, useRef } from "react"
import { Input } from "@/components/ui/input"
import { Search, X, SlidersHorizontal } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SearchFilterBarProps {
  placeholder?: string
  categories?: string[]
  initialCategory?: string
  initialQuery?: string
  onSearchChange?: (query: string, selectedCategory: string) => void
  totalCount?: number
  debounceMs?: number
  className?: string
}

export function SearchFilterBar({
  placeholder = "Search by keyword, name, or tag...",
  categories = ["All", "Services", "Products", "Articles", "Events"],
  initialCategory = "All",
  initialQuery = "",
  onSearchChange,
  totalCount,
  debounceMs = 300,
  className,
}: SearchFilterBarProps) {
  const [query, setQuery] = useState(initialQuery)
  const [selectedCategory, setSelectedCategory] = useState(initialCategory)
  const isFirstRender = useRef(true)

  // Debounce search updates
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }

    const timer = setTimeout(() => {
      onSearchChange?.(query.trim(), selectedCategory)
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [query, selectedCategory, debounceMs, onSearchChange])

  const handleClear = () => {
    setQuery("")
    onSearchChange?.("", selectedCategory)
  }

  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(cat)
    onSearchChange?.(query.trim(), cat)
  }

  return (
    <div
      role="search"
      aria-label="Filter and Search"
      className={cn("w-full py-6 px-4 sm:px-6 max-w-5xl mx-auto space-y-4", className)}
    >
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="pl-10 pr-9 h-11 text-sm bg-card border-border shadow-xs rounded-xl"
            aria-label="Search items"
          />
          {query && (
            <button
              type="button"
              onClick={handleClear}
              aria-label="Clear search input"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Results Counter */}
        {totalCount !== undefined && (
          <div className="shrink-0 text-xs text-muted-foreground px-3 py-2 bg-muted/60 border border-border rounded-xl text-center">
            Found <strong className="text-foreground tabular-nums">{totalCount}</strong> results
          </div>
        )}
      </div>

      {/* Category Filter Chips */}
      {categories && categories.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mr-1">
            <SlidersHorizontal className="h-3 w-3" />
            <span>Category:</span>
          </div>
          {categories.map((cat) => {
            const isActive = selectedCategory.toLowerCase() === cat.toLowerCase()
            return (
              <button
                key={cat}
                type="button"
                onClick={() => handleCategoryClick(cat)}
                className={cn(
                  "px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                )}
              >
                {cat}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
