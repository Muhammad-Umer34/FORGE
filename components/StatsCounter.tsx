// Stats & Metrics Counter: Numbers and achievement metrics displaying verifiable impact, patients served, or project scale

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Users, Award, ShieldCheck, HeartHandshake } from "lucide-react"
import { cn } from "@/lib/utils"

export interface StatItem {
  value: string
  label: string
  description?: string
  trend?: string
}

export interface StatsCounterProps {
  badgeText?: string
  title?: string
  subtitle?: string
  stats?: StatItem[]
  className?: string
}

export function StatsCounter({
  badgeText = "Proven Track Record",
  title = "Impact Measured in Real Numbers",
  subtitle = "Our commitment to quality, patient outcomes, and clinical reliability is reflected in our sustained track record.",
  stats = [
    {
      value: "15,000+",
      label: "Patients Treated",
      description: "Delivering gentle, compassionate care across all age groups since 2012.",
      trend: "+12% this year",
    },
    {
      value: "99.4%",
      label: "Satisfaction Rate",
      description: "Independently verified 5-star patient reviews and recommendations.",
      trend: "5-Star Average",
    },
    {
      value: "18+",
      label: "Years of Practice",
      description: "Continuous clinical operation backed by board-certified practitioners.",
      trend: "Est. 2008",
    },
    {
      value: "24/7",
      label: "Emergency Support",
      description: "Dedicated same-day clinical walk-in access for acute relief.",
      trend: "Always on call",
    },
  ],
  className,
}: StatsCounterProps) {
  return (
    <section
      id="stats"
      className={cn(
        "w-full py-16 sm:py-20 bg-background/50 border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-12 sm:mb-16">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            {title}
          </h2>
          {subtitle && (
            <p className="text-base text-muted-foreground leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {/* Counter Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {stats.map((stat, idx) => (
            <div
              key={idx}
              className="relative p-6 sm:p-8 rounded-2xl border border-border bg-card/60 backdrop-blur shadow-sm hover:border-primary/40 transition-all duration-300 text-center flex flex-col justify-between"
            >
              <div>
                <div className="text-4xl sm:text-5xl font-black text-foreground tracking-tight mb-2 bg-gradient-to-r from-foreground via-foreground/90 to-primary bg-clip-text text-transparent">
                  {stat.value}
                </div>
                <h3 className="font-semibold text-base text-foreground mb-1.5">
                  {stat.label}
                </h3>
                {stat.description && (
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {stat.description}
                  </p>
                )}
              </div>

              {stat.trend && (
                <div className="mt-4 pt-3 border-t border-border/50 text-[11px] font-medium text-success flex items-center justify-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5" />
                  {stat.trend}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
