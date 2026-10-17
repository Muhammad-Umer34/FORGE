// High-impact hero section with badge, main headline, description, primary and secondary CTA buttons, and optional showcase image

"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export interface HeroProps {
  badgeText?: string
  headline?: string
  subheadline?: string
  primaryCtaText?: string
  primaryCtaHref?: string
  onPrimaryCtaClick?: () => void
  secondaryCtaText?: string
  secondaryCtaHref?: string
  onSecondaryCtaClick?: () => void
  imageUrl?: string
  imageAlt?: string
  align?: "center" | "left"
  className?: string
}

export function Hero({
  badgeText = "Next-Gen AI Website Engine",
  headline = "Build Production Websites in Seconds with AI",
  subheadline = "Transform simple text prompts into full-stack, responsive websites with WebContainers, shadcn/ui components, and instant real-time live preview.",
  primaryCtaText = "Start Building Free",
  primaryCtaHref = "#build",
  onPrimaryCtaClick,
  secondaryCtaText = "Explore Components",
  secondaryCtaHref = "#library",
  onSecondaryCtaClick,
  imageUrl,
  imageAlt = "Product Preview Showcase",
  align = "center",
  className,
}: HeroProps) {
  const isCentered = align === "center"

  return (
    <section
      className={cn(
        "relative w-full py-16 sm:py-24 lg:py-32 overflow-hidden bg-background border-b border-border/40",
        className
      )}
    >
      {/* Subtle Background Glow */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div
          className={cn(
            "flex flex-col",
            isCentered ? "items-center text-center max-w-3xl mx-auto" : "items-start text-left max-w-2xl"
          )}
        >
          {/* Badge */}
          {badgeText && (
            <div className="mb-4">
              <Badge
                variant="secondary"
                className="gap-1.5 px-3 py-1 text-xs sm:text-sm font-medium border border-primary/20 text-foreground bg-primary/10 hover:bg-primary/20 transition-colors"
              >
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                {badgeText}
              </Badge>
            </div>
          )}

          {/* Main Headline */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-[1.15]">
            {headline}
          </h1>

          {/* Subheadline / Description */}
          {subheadline && (
            <p className="mt-4 sm:mt-6 text-base sm:text-lg lg:text-xl text-muted-foreground leading-relaxed">
              {subheadline}
            </p>
          )}

          {/* Call-to-action buttons */}
          <div className="mt-8 flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
            {primaryCtaText && (
              <Button
                size="lg"
                onClick={onPrimaryCtaClick}
                asChild={!onPrimaryCtaClick && Boolean(primaryCtaHref)}
                className="w-full sm:w-auto gap-2 font-semibold shadow-md"
              >
                {onPrimaryCtaClick ? (
                  <>
                    {primaryCtaText} <ArrowRight className="h-4 w-4" />
                  </>
                ) : (
                  <a href={primaryCtaHref}>
                    {primaryCtaText} <ArrowRight className="h-4 w-4" />
                  </a>
                )}
              </Button>
            )}

            {secondaryCtaText && (
              <Button
                variant="outline"
                size="lg"
                onClick={onSecondaryCtaClick}
                asChild={!onSecondaryCtaClick && Boolean(secondaryCtaHref)}
                className="w-full sm:w-auto font-medium"
              >
                {onSecondaryCtaClick ? (
                  secondaryCtaText
                ) : (
                  <a href={secondaryCtaHref}>{secondaryCtaText}</a>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Optional Hero Visual Showcase */}
        {imageUrl && (
          <div className="mt-12 sm:mt-16 relative rounded-2xl border border-border bg-card p-2 sm:p-4 shadow-2xl overflow-hidden max-w-5xl mx-auto">
            <div className="rounded-xl overflow-hidden bg-muted aspect-video relative flex items-center justify-center">
              <img
                src={imageUrl}
                alt={imageAlt}
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
