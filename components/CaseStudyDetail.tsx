// Comprehensive project case study template detailing challenge, solution, quantifiable results, and project screenshots

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ExternalLink, Target, Lightbulb, TrendingUp, Layers, Calendar, User } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CaseStudyMetric {
  label: string
  value: string
}

export interface CaseStudyGalleryItem {
  src: string
  alt?: string
  caption?: string
}

export interface CaseStudyDetailProps {
  badgeText?: string
  title?: string
  clientName?: string
  year?: string
  role?: string
  summary?: string
  challenge?: string
  solution?: string
  result?: string
  metrics?: CaseStudyMetric[]
  gallery?: CaseStudyGalleryItem[]
  liveUrl?: string
  className?: string
}

export function CaseStudyDetail({
  badgeText = "Featured Case Study",
  title = "Complete Brand Identity & Digital Experience Transformation",
  clientName = "Artisan Food Co.",
  year = "2026",
  role = "Lead Product Designer & Developer",
  summary = "How we helped a beloved local food producer modernize their digital ordering system, reduce checkout friction, and boost repeat orders by 35%.",
  challenge = "The client relied on legacy phone calls and manual paper order sheets during seasonal peak periods. Long confirmation hold times caused missed customer reservations and substantial administrative strain on staff.",
  solution = "We designed and launched an automated mobile-first ordering portal featuring clear product photography, real-time date availability, and automatic customer message notifications.",
  result = "Order processing overhead dropped by 75% within the first month. The customer satisfaction score rose to 98%, and holiday pre-orders sold out in record time.",
  metrics = [
    { label: "Increase in Orders", value: "+35%" },
    { label: "Admin Time Saved", value: "75%" },
    { label: "Customer Rating", value: "4.9/5" },
  ],
  gallery = [
    {
      src: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80",
      alt: "Interface analytics and ordering layout",
      caption: "Mobile-optimized ordering interface and item selection flow.",
    },
    {
      src: "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1200&q=80",
      alt: "Client review and production fulfillment",
      caption: "Real-time kitchen order dispatch and fulfillment view.",
    },
  ],
  liveUrl,
  className,
}: CaseStudyDetailProps) {
  return (
    <article className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
        {/* Header Block */}
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            {badgeText && (
              <Badge variant="outline" className="text-primary border-primary/30">
                {badgeText}
              </Badge>
            )}
            {clientName && (
              <Badge variant="secondary" className="text-xs">
                {clientName}
              </Badge>
            )}
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-foreground leading-tight">
            {title}
          </h1>

          {summary && (
            <p className="text-base sm:text-xl text-muted-foreground leading-relaxed max-w-3xl">
              {summary}
            </p>
          )}

          {/* Project Metadata Ribbon */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-5 rounded-xl bg-card border border-border text-xs">
            <div>
              <span className="text-muted-foreground block">Client:</span>
              <strong className="text-foreground font-semibold">{clientName}</strong>
            </div>
            <div>
              <span className="text-muted-foreground block">Year:</span>
              <strong className="text-foreground font-semibold">{year}</strong>
            </div>
            <div>
              <span className="text-muted-foreground block">Role:</span>
              <strong className="text-foreground font-semibold">{role}</strong>
            </div>
            {liveUrl && (
              <div className="flex items-center">
                <Button asChild size="sm" variant="outline" className="h-8 gap-1.5 text-xs">
                  <a href={liveUrl} target="_blank" rel="noopener noreferrer">
                    Live Project <ExternalLink className="h-3 w-3" />
                  </a>
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Quantifiable Metrics Strip */}
        {metrics && metrics.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {metrics.map((m, idx) => (
              <Card key={idx} className="border-border bg-card p-6 text-center shadow-xs">
                <div className="text-3xl sm:text-4xl font-black text-primary mb-1">{m.value}</div>
                <div className="text-xs text-muted-foreground font-medium">{m.label}</div>
              </Card>
            ))}
          </div>
        )}

        {/* Narrative Deep Dive: Challenge, Solution, Result */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Challenge */}
          <Card className="border-border bg-card p-6 space-y-3">
            <div className="h-10 w-10 rounded-xl bg-destructive/10 text-destructive flex items-center justify-center">
              <Target className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-lg text-foreground">The Challenge</h3>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              {challenge}
            </p>
          </Card>

          {/* Solution */}
          <Card className="border-border bg-card p-6 space-y-3">
            <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <Lightbulb className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-lg text-foreground">The Solution</h3>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              {solution}
            </p>
          </Card>

          {/* Result */}
          <Card className="border-border bg-card p-6 space-y-3">
            <div className="h-10 w-10 rounded-xl bg-success/10 text-success flex items-center justify-center">
              <TrendingUp className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-lg text-foreground">The Result</h3>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              {result}
            </p>
          </Card>
        </div>

        {/* Project Gallery Screenshots */}
        {gallery && gallery.length > 0 && (
          <div className="space-y-6">
            <h3 className="text-xl font-bold text-foreground">Project Gallery</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {gallery.map((img, idx) => (
                <div key={idx} className="space-y-2">
                  <div className="aspect-[16/10] rounded-xl overflow-hidden bg-muted border border-border">
                    <img src={img.src} alt={img.alt || title} className="h-full w-full object-cover" />
                  </div>
                  {img.caption && (
                    <p className="text-xs text-muted-foreground pl-1">{img.caption}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  )
}
