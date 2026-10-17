// Vertical milestone timeline showcasing company history, key achievements, and growth journey

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { CheckCircle2, History, Milestone, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export interface TimelineItem {
  id: string
  date: string // e.g. "2022" or "January 2026"
  title: string
  description: string
  tag?: string
}

export interface TimelineProps {
  badgeText?: string
  title?: string
  subtitle?: string
  items?: TimelineItem[]
  className?: string
}

export function Timeline({
  badgeText = "Our Journey",
  title = "Company Milestones & History",
  subtitle = "Tracing our evolution from a modest neighborhood workshop to an established community brand.",
  items = [
    {
      id: "time-1",
      date: "2020",
      title: "Founding & First Workshop",
      description: "Started in a small shared kitchen space with a single woodfire oven and a passion for slow fermentation.",
      tag: "Origins",
    },
    {
      id: "time-2",
      date: "2022",
      title: "Opening Our Flagship Storefront",
      description: "Secured our permanent retail location, expanding daily capacity and introducing neighborhood coffee service.",
      tag: "Expansion",
    },
    {
      id: "time-3",
      date: "2024",
      title: "Regional Sourcing Certification",
      description: "Partnered directly with local family farms to transition 100% of our organic grain sourcing to regional mills.",
      tag: "Sustainability",
    },
    {
      id: "time-4",
      date: "2026",
      title: "Online Ordering & Masterclasses",
      description: "Launched our digital pre-ordering system and community weekend masterclasses for aspiring artisan bakers.",
      tag: "Present",
    },
  ],
  className,
}: TimelineProps) {
  if (!items || items.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <History className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No timeline entries available.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="timeline" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-3xl mx-auto text-center space-y-3 mb-16">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground">{subtitle}</p>}
        </div>

        {/* Vertical Timeline Spine */}
        <div className="relative border-l-2 border-border/80 ml-4 sm:ml-32 md:ml-40 space-y-12">
          {items.map((item, idx) => (
            <div key={item.id} className="relative pl-6 sm:pl-8 group">
              {/* Bullet Node */}
              <div className="absolute -left-[9px] top-1.5 h-4 w-4 rounded-full bg-background border-2 border-primary group-hover:bg-primary transition-colors flex items-center justify-center">
                <div className="h-1.5 w-1.5 rounded-full bg-primary group-hover:bg-white" />
              </div>

              {/* Date Marker (on left for sm+ screens) */}
              <div className="sm:absolute sm:-left-36 md:-left-44 sm:top-1 sm:w-28 md:w-36 sm:text-right">
                <span className="text-xs sm:text-sm font-extrabold text-primary tracking-wide tabular-nums uppercase">
                  {item.date}
                </span>
              </div>

              {/* Milestone Content Card */}
              <Card className="border-border bg-card p-6 shadow-sm hover:border-primary/40 transition-colors">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-bold text-lg text-foreground">{item.title}</h3>
                    {item.tag && (
                      <Badge variant="secondary" className="text-[10px] font-medium py-0 px-2">
                        {item.tag}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </Card>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
