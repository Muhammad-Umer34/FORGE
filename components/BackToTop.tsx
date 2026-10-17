// Floating scroll-to-top navigation button with smooth scrolling and reduced-motion compliance

"use client"

import React, { useState, useEffect } from "react"
import { ArrowUp } from "lucide-react"
import { cn } from "@/lib/utils"

export interface BackToTopProps {
  threshold?: number
  label?: string
  showLabel?: boolean
  position?: "bottom-right" | "bottom-left"
  className?: string
}

export function BackToTop({
  threshold = 300,
  label = "Back to top",
  showLabel = false,
  position = "bottom-right",
  className,
}: BackToTopProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined") return

    const handleScroll = () => {
      const scrollY = window.scrollY || document.documentElement.scrollTop
      setIsVisible(scrollY > threshold)
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    handleScroll()

    return () => window.removeEventListener("scroll", handleScroll)
  }, [threshold])

  const scrollToTop = () => {
    if (typeof window === "undefined") return

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion ? "auto" : "smooth",
    })
  }

  if (!isVisible) {
    return null
  }

  const positionClasses =
    position === "bottom-left" ? "bottom-6 left-6" : "bottom-6 right-6"

  return (
    <aside
      aria-label="Back to Top Navigation"
      className={cn("fixed z-40 animate-in fade-in zoom-in-95 duration-200", positionClasses, className)}
    >
      <button
        type="button"
        onClick={scrollToTop}
        aria-label={label}
        className={cn(
          "group flex items-center justify-center gap-2 p-3 sm:p-3.5 rounded-full shadow-lg",
          "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95",
          "transition-all duration-200 border border-primary/20",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        )}
      >
        <ArrowUp className="h-5 w-5 transition-transform group-hover:-translate-y-0.5" />
        {showLabel && (
          <span className="text-xs font-bold pr-1">{label}</span>
        )}
      </button>
    </aside>
  )
}
