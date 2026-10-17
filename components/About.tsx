// About section with story narrative, key numerical statistics, feature highlights, and optional team or founder image

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { CheckCircle, Users } from "lucide-react"
import { cn } from "@/lib/utils"

export interface AboutStat {
  label: string
  value: string
}

export interface AboutFeature {
  title: string
  description: string
}

export interface AboutProps {
  badgeText?: string
  title?: string
  subtitle?: string
  story?: string
  stats?: AboutStat[]
  features?: AboutFeature[]
  imageUrl?: string
  imageAlt?: string
  className?: string
}

export function About({
  badgeText = "About Us",
  title = "Crafting Exceptional Quality & Memorable Experiences",
  subtitle = "Dedicated to passion, authenticity, and customer satisfaction.",
  story = "Founded with a commitment to excellence, our team combines traditional craftsmanship with modern innovation. We take pride in serving our community with top-tier products, unparalleled service, and relentless attention to detail.",
  stats = [
    { value: "100%", label: "Customer Satisfaction" },
    { value: "5+", label: "Years of Excellence" },
    { value: "10k+", label: "Happy Clients Served" },
    { value: "100%", label: "Locally Sourced" },
  ],
  features = [
    {
      title: "Handcrafted Quality",
      description: "Every item is crafted daily using premium, carefully selected ingredients and materials.",
    },
    {
      title: "Community Focused",
      description: "We work directly with local producers and partners to support our regional ecosystem.",
    },
    {
      title: "Guaranteed Freshness",
      description: "Uncompromising standards ensure you receive peak quality with every order.",
    },
  ],
  imageUrl,
  imageAlt = "About our story and values",
  className,
}: AboutProps) {
  return (
    <section
      id="about"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left Column: Narrative & Stats */}
          <div className="space-y-6">
            {badgeText && (
              <Badge variant="outline" className="text-primary border-primary/30">
                {badgeText}
              </Badge>
            )}

            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground leading-tight">
              {title}
            </h2>

            {subtitle && (
              <p className="text-lg font-medium text-muted-foreground">
                {subtitle}
              </p>
            )}

            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
              {story}
            </p>

            {/* Numerical Statistics Grid */}
            {stats && stats.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border/60">
                {stats.map((stat, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="text-2xl sm:text-3xl font-black text-primary">
                      {stat.value}
                    </div>
                    <div className="text-xs text-muted-foreground font-medium">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Features List or Showcase Image */}
          <div className="space-y-4">
            {imageUrl ? (
              <div className="relative rounded-2xl overflow-hidden border border-border shadow-lg aspect-4/3">
                <img
                  src={imageUrl}
                  alt={imageAlt}
                  className="w-full h-full object-cover"
                />
              </div>
            ) : (
              <div className="space-y-3">
                {features.map((feat, idx) => (
                  <Card key={idx} className="border-border/60 bg-card/60 backdrop-blur">
                    <CardContent className="p-5 flex items-start gap-4">
                      <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
                        <CheckCircle className="h-4 w-4" />
                      </div>
                      <div className="space-y-1">
                        <h4 className="font-semibold text-sm sm:text-base text-foreground">
                          {feat.title}
                        </h4>
                        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                          {feat.description}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
