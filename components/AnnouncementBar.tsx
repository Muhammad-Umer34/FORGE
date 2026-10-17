// Thin top notification ribbon banner with action link and session-remembered dismiss button

"use client"

import React, { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { X, ArrowRight, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export interface AnnouncementBarProps {
  badgeText?: string
  message?: string
  linkText?: string
  linkHref?: string
  storageKey?: string
  className?: string
}

export function AnnouncementBar({
  badgeText = "New",
  message = "Holiday pre-orders are now officially open for delivery and pickup.",
  linkText = "Learn More",
  linkHref = "#order-request",
  storageKey = "forge_announcement_bar_dismissed",
  className,
}: AnnouncementBarProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const isDismissed = sessionStorage.getItem(storageKey) === "true"
        if (!isDismissed) {
          setIsVisible(true)
        }
      } catch {
        setIsVisible(true)
      }
    }
  }, [storageKey])

  const handleDismiss = () => {
    setIsVisible(false)
    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(storageKey, "true")
      } catch {
        // Ignore storage exceptions
      }
    }
  }

  if (!isVisible) {
    return null
  }

  return (
    <aside
      role="banner"
      aria-label="Announcement"
      className={cn(
        "relative w-full bg-primary text-primary-foreground py-2.5 px-4 text-xs font-medium z-30 transition-all",
        className
      )}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Center message & optional link */}
        <div className="flex-1 flex flex-wrap items-center justify-center gap-2 text-center">
          {badgeText && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-primary-foreground/20 text-primary-foreground">
              {badgeText}
            </span>
          )}
          <span>{message}</span>
          {linkText && linkHref && (
            <a
              href={linkHref}
              className="inline-flex items-center gap-1 font-bold underline underline-offset-2 hover:opacity-90 ml-1"
            >
              {linkText}
              <ArrowRight className="h-3 w-3" />
            </a>
          )}
        </div>

        {/* Dismiss Button */}
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss announcement"
          className="p-1 rounded-md hover:bg-primary-foreground/20 text-primary-foreground transition-colors shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </aside>
  )
}
