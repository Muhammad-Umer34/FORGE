// Universal loading skeletons and accessible error boundary states for data-driven sections

"use client"

import React from "react"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

export type SkeletonType = "card-grid" | "form" | "table" | "list" | "hero"

export interface ComponentSkeletonProps {
  type?: SkeletonType
  count?: number
  className?: string
}

export function ComponentSkeleton({
  type = "card-grid",
  count = 3,
  className,
}: ComponentSkeletonProps) {
  if (type === "hero") {
    return (
      <div className={cn("w-full py-16 px-4 max-w-5xl mx-auto space-y-6 text-center", className)}>
        <Skeleton className="h-6 w-32 mx-auto rounded-full" />
        <Skeleton className="h-12 w-3/4 max-w-xl mx-auto rounded-lg" />
        <Skeleton className="h-6 w-1/2 max-w-md mx-auto rounded-md" />
        <div className="flex justify-center gap-3 pt-4">
          <Skeleton className="h-11 w-32 rounded-lg" />
          <Skeleton className="h-11 w-32 rounded-lg" />
        </div>
      </div>
    )
  }

  if (type === "form") {
    return (
      <div className={cn("w-full py-12 px-4 max-w-xl mx-auto space-y-4", className)}>
        <Skeleton className="h-8 w-48 mb-4 rounded-md" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-20 rounded" />
          <Skeleton className="h-10 w-full rounded-md" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-24 rounded" />
          <Skeleton className="h-10 w-full rounded-md" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-28 rounded" />
          <Skeleton className="h-24 w-full rounded-md" />
        </div>
        <Skeleton className="h-11 w-full rounded-md mt-4" />
      </div>
    )
  }

  if (type === "table") {
    return (
      <div className={cn("w-full py-8 px-4 max-w-4xl mx-auto space-y-3", className)}>
        <Skeleton className="h-8 w-40 mb-4 rounded-md" />
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex justify-between items-center p-4 border border-border rounded-xl">
            <Skeleton className="h-5 w-32 rounded" />
            <Skeleton className="h-5 w-24 rounded" />
          </div>
        ))}
      </div>
    )
  }

  if (type === "list") {
    return (
      <div className={cn("w-full py-8 px-4 max-w-4xl mx-auto space-y-4", className)}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex gap-4 items-start p-4 border border-border rounded-xl">
            <Skeleton className="h-14 w-14 rounded-lg shrink-0" />
            <div className="space-y-2 flex-1">
              <Skeleton className="h-5 w-1/3 rounded" />
              <Skeleton className="h-4 w-3/4 rounded" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Default: card-grid
  return (
    <div
      className={cn(
        "w-full py-12 px-4 max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6",
        className
      )}
    >
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="border-border bg-card overflow-hidden">
          <Skeleton className="aspect-square w-full rounded-none" />
          <CardContent className="p-5 space-y-3">
            <Skeleton className="h-5 w-3/4 rounded" />
            <Skeleton className="h-4 w-1/2 rounded" />
            <Skeleton className="h-9 w-full rounded-md mt-4" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export interface ComponentErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  retryLabel?: string
  className?: string
}

export function ComponentErrorState({
  title = "Failed to Load Section",
  message = "An error occurred while retrieving data for this section. Please try again or check back later.",
  onRetry,
  retryLabel = "Try Again",
  className,
}: ComponentErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "w-full py-12 px-4 max-w-md mx-auto text-center space-y-4",
        className
      )}
    >
      <Card className="p-8 border-destructive/20 bg-destructive/5 shadow-xs">
        <div className="h-12 w-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto mb-3">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h3 className="text-lg font-bold text-foreground mb-1">{title}</h3>
        <p className="text-xs text-muted-foreground leading-relaxed mb-6">{message}</p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="gap-2 text-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {retryLabel}
          </Button>
        )}
      </Card>
    </div>
  )
}
