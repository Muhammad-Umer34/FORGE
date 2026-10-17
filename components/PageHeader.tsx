// Inner page header banner with breadcrumb navigation, title, descriptive subtitle, and optional hero background image

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { ChevronRight, Home } from "lucide-react"
import { cn } from "@/lib/utils"

export interface BreadcrumbItem {
  label: string
  href?: string
  isCurrent?: boolean
}

export interface PageHeaderProps {
  badgeText?: string
  title?: string
  subtitle?: string
  breadcrumbs?: BreadcrumbItem[]
  backgroundImageUrl?: string
  alignment?: "center" | "left"
  className?: string
}

export function PageHeader({
  badgeText,
  title = "Page Title",
  subtitle = "A descriptive overview providing context for the content presented on this page.",
  breadcrumbs = [
    { label: "Home", href: "/" },
    { label: "Section", href: "#" },
    { label: "Current Page", isCurrent: true },
  ],
  backgroundImageUrl,
  alignment = "center",
  className,
}: PageHeaderProps) {
  const isCentered = alignment === "center"
  const hasBgImage = Boolean(backgroundImageUrl && backgroundImageUrl.trim().length > 0)

  return (
    <header
      className={cn(
        "relative w-full py-16 sm:py-24 border-b border-border/40 overflow-hidden",
        hasBgImage ? "bg-zinc-950 text-white" : "bg-muted/30 text-foreground",
        className
      )}
    >
      {/* Background Image & Contrast Protection Overlay */}
      {hasBgImage && (
        <>
          <div
            className="absolute inset-0 bg-cover bg-center filter brightness-50"
            style={{ backgroundImage: `url(${backgroundImageUrl})` }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/70 to-zinc-950/40" />
        </>
      )}

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb Navigation */}
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav
            aria-label="Breadcrumbs"
            className={cn("flex mb-6", isCentered ? "justify-center" : "justify-start")}
          >
            <ol className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
              {breadcrumbs.map((crumb, idx) => {
                const isLast = idx === breadcrumbs.length - 1 || crumb.isCurrent

                return (
                  <li key={idx} className="flex items-center gap-1.5">
                    {idx === 0 && <Home className="h-3.5 w-3.5 opacity-70" />}
                    {isLast ? (
                      <span
                        className={cn("font-semibold", hasBgImage ? "text-white" : "text-foreground")}
                        aria-current="page"
                      >
                        {crumb.label}
                      </span>
                    ) : (
                      <a
                        href={crumb.href || "#"}
                        className={cn(
                          "hover:underline transition-colors",
                          hasBgImage ? "text-zinc-300 hover:text-white" : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {crumb.label}
                      </a>
                    )}
                    {!isLast && <ChevronRight className="h-3 w-3 opacity-40 shrink-0" />}
                  </li>
                )
              })}
            </ol>
          </nav>
        )}

        {/* Content Box */}
        <div className={cn("max-w-3xl space-y-4", isCentered ? "mx-auto text-center" : "text-left")}>
          {badgeText && (
            <Badge
              variant="outline"
              className={cn(
                "border-primary/30",
                hasBgImage ? "text-white border-white/20 bg-white/10" : "text-primary"
              )}
            >
              {badgeText}
            </Badge>
          )}

          <h1
            className={cn(
              "text-3xl sm:text-5xl font-black tracking-tight",
              hasBgImage ? "text-white" : "text-foreground"
            )}
          >
            {title}
          </h1>

          {subtitle && (
            <p
              className={cn(
                "text-base sm:text-lg leading-relaxed max-w-2xl",
                isCentered && "mx-auto",
                hasBgImage ? "text-zinc-300" : "text-muted-foreground"
              )}
            >
              {subtitle}
            </p>
          )}
        </div>
      </div>
    </header>
  )
}
