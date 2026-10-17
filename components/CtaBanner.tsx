// Call to Action (CTA) Banner: High-impact conversion strip with background glow, compelling headline, and dual action buttons

"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, Sparkles, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CtaBannerProps {
  badgeText?: string
  headline?: string
  subheadline?: string
  primaryCtaText?: string
  secondaryCtaText?: string
  primaryCtaLink?: string
  secondaryCtaLink?: string
  highlights?: string[]
  className?: string
}

export function CtaBanner({
  badgeText = "Get Started Today",
  headline = "Ready to Experience the Difference?",
  subheadline = "Join thousands of satisfied clients who trust our dedicated team. Book your initial consultation or appointment online in less than two minutes.",
  primaryCtaText = "Book an Appointment",
  secondaryCtaText = "Contact Support",
  primaryCtaLink = "#booking",
  secondaryCtaLink = "#contact",
  highlights = [
    "No Credit Card Required",
    "Instant Confirmation",
    "Free Initial Evaluation",
  ],
  className,
}: CtaBannerProps) {
  return (
    <section
      id="cta"
      className={cn(
        "w-full py-16 sm:py-20 relative overflow-hidden bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-primary/10 via-card/80 to-card/40 border border-primary/20 p-8 sm:p-12 lg:p-16 text-center shadow-xl backdrop-blur">
          {/* Subtle Ambient Radial Glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-primary/20 rounded-full blur-3xl -z-10 pointer-events-none" />

          {/* Badge */}
          {badgeText && (
            <div className="inline-flex items-center gap-1.5 mb-6">
              <Badge variant="secondary" className="px-3 py-1 text-xs font-semibold bg-primary/20 text-primary border-primary/30">
                <Sparkles className="h-3.5 w-3.5 mr-1" />
                {badgeText}
              </Badge>
            </div>
          )}

          {/* Headline & Subheadline */}
          <div className="max-w-3xl mx-auto space-y-4 mb-8 sm:mb-10">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-foreground leading-tight">
              {headline}
            </h2>
            <p className="text-base sm:text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
              {subheadline}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto">
            {primaryCtaText && (
              <Button
                asChild
                size="lg"
                className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-8 h-12 rounded-xl shadow-lg shadow-primary/25 gap-2"
              >
                <a href={primaryCtaLink}>
                  {primaryCtaText}
                  <ArrowRight className="h-4 w-4" />
                </a>
              </Button>
            )}

            {secondaryCtaText && (
              <Button
                asChild
                variant="outline"
                size="lg"
                className="w-full sm:w-auto border-border hover:bg-muted/60 font-medium px-8 h-12 rounded-xl"
              >
                <a href={secondaryCtaLink}>
                  {secondaryCtaText}
                </a>
              </Button>
            )}
          </div>

          {/* Trust Highlights Strip */}
          {highlights && highlights.length > 0 && (
            <div className="mt-8 pt-8 border-t border-border/40 flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
              {highlights.map((highlight, hIdx) => (
                <div key={hIdx} className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  <span>{highlight}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
