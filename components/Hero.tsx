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
  /** Layout chosen in the site's design direction (D-224). Without an image, "split" and "full-bleed" show as "centred". */
  variant?: "centred" | "split" | "full-bleed" | "editorial"
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
  variant = "centred",
  className,
}: HeroProps) {
  const layout = !imageUrl && (variant === "split" || variant === "full-bleed") ? "centred" : variant
  const onPhoto = layout === "full-bleed"
  const centred = layout === "centred" || onPhoto

  const text = (
    <div className={cn("flex flex-col", centred ? "items-center text-center max-w-3xl mx-auto" : "items-start text-left")}>
      {badgeText && (
        <div className="mb-4">
          <Badge
            variant="secondary"
            className={cn(
              "gap-1.5 px-3 py-1 text-xs sm:text-sm font-medium border",
              onPhoto ? "border-white/30 bg-white/15 text-white" : "border-primary/20 text-foreground bg-primary/10"
            )}
          >
            <Sparkles className={cn("h-3.5 w-3.5", onPhoto ? "text-white" : "text-primary")} />
            {badgeText}
          </Badge>
        </div>
      )}

      <h1
        className={cn(
          "font-extrabold tracking-tight leading-[1.1]",
          layout === "editorial" ? "text-4xl sm:text-6xl lg:text-7xl" : "text-3xl sm:text-5xl lg:text-6xl",
          onPhoto ? "text-white" : "text-foreground"
        )}
      >
        {headline}
      </h1>

      {subheadline && (
        <p
          className={cn(
            "mt-4 sm:mt-6 text-base sm:text-lg lg:text-xl leading-relaxed",
            onPhoto ? "text-white/85" : "text-muted-foreground",
            layout === "editorial" && "max-w-2xl"
          )}
        >
          {subheadline}
        </p>
      )}

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
            className={cn("w-full sm:w-auto font-medium", onPhoto && "border-white/40 bg-transparent text-white hover:bg-white/10")}
          >
            {onSecondaryCtaClick ? secondaryCtaText : <a href={secondaryCtaHref}>{secondaryCtaText}</a>}
          </Button>
        )}
      </div>
    </div>
  )

  if (onPhoto) {
    return (
      <section className={cn("relative w-full overflow-hidden border-b border-border/40", className)}>
        <img src={imageUrl} alt={imageAlt} className="absolute inset-0 h-full w-full object-cover" />
        {/* fixed dark scrim: text over a photo must stay readable on any picture */}
        <div className="absolute inset-0 bg-black/55" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 lg:py-40">{text}</div>
      </section>
    )
  }

  return (
    <section
      className={cn(
        "relative w-full py-16 sm:py-24 lg:py-32 overflow-hidden bg-background border-b border-border/40",
        className
      )}
    >
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        {layout === "split" ? (
          <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
            {text}
            <div className="relative overflow-hidden rounded-2xl border border-border bg-muted shadow-xl aspect-[4/3]">
              <img src={imageUrl} alt={imageAlt} className="h-full w-full object-cover" />
            </div>
          </div>
        ) : (
          <>
            <div className={cn(layout === "editorial" && "border-t-4 border-primary pt-8 sm:pt-10 max-w-4xl")}>{text}</div>
            {imageUrl && (
              <div
                className={cn(
                  "mt-12 sm:mt-16 relative overflow-hidden",
                  layout === "editorial"
                    ? "rounded-xl aspect-[21/9]"
                    : "rounded-2xl border border-border bg-card p-2 sm:p-4 shadow-2xl max-w-5xl mx-auto"
                )}
              >
                <div className={cn("overflow-hidden bg-muted relative h-full", layout !== "editorial" && "rounded-xl aspect-video")}>
                  <img src={imageUrl} alt={imageAlt} className="w-full h-full object-cover" />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
