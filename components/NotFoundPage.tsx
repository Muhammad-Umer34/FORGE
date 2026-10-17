// Friendly, accessible 404 error page layout with clear navigational recovery links

"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Home, ArrowLeft, HelpCircle, Compass } from "lucide-react"
import { cn } from "@/lib/utils"

export interface NotFoundPageProps {
  title?: string
  subtitle?: string
  homeLabel?: string
  homeHref?: string
  supportLabel?: string
  supportHref?: string
  className?: string
}

export function NotFoundPage({
  title = "Page Not Found",
  subtitle = "The page you are looking for may have been moved, renamed, or is temporarily unavailable.",
  homeLabel = "Return to Homepage",
  homeHref = "/",
  supportLabel = "Contact Support",
  supportHref = "#contact",
  className,
}: NotFoundPageProps) {
  return (
    <div
      role="main"
      className={cn(
        "min-h-[70vh] w-full flex items-center justify-center py-20 px-4 sm:px-6 lg:px-8 bg-background text-foreground",
        className
      )}
    >
      <div className="max-w-md w-full text-center space-y-8 animate-in fade-in duration-300">
        {/* Visual Badge */}
        <div className="relative mx-auto w-24 h-24 rounded-3xl bg-primary/10 text-primary flex items-center justify-center border border-primary/20 shadow-sm">
          <Compass className="h-12 w-12 animate-pulse" />
          <span className="absolute -bottom-2 -right-2 px-2.5 py-0.5 rounded-full text-xs font-black bg-primary text-primary-foreground shadow-xs">
            404
          </span>
        </div>

        {/* Messaging */}
        <div className="space-y-3">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">
            {title}
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            {subtitle}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Button asChild className="w-full sm:w-auto gap-2">
            <a href={homeHref}>
              <Home className="h-4 w-4" />
              {homeLabel}
            </a>
          </Button>

          {supportLabel && supportHref && (
            <Button asChild variant="outline" className="w-full sm:w-auto gap-2">
              <a href={supportHref}>
                <HelpCircle className="h-4 w-4" />
                {supportLabel}
              </a>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
