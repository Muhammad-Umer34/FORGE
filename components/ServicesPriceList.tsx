// Itemised services price list with starting price indicators, estimated session durations, and descriptive service notes

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Clock, ArrowRight, Sparkles, Tag } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ServicePriceItem {
  id: string
  name: string
  price: string
  isStartingPrice?: boolean // e.g. displays "from $45"
  duration?: string // e.g. "45 mins"
  description?: string
  category?: string
  badge?: string
}

export interface ServicesPriceListProps {
  badgeText?: string
  title?: string
  subtitle?: string
  services?: ServicePriceItem[]
  categories?: string[]
  footnote?: string
  bookingCtaText?: string
  bookingCtaHref?: string
  className?: string
}

export function ServicesPriceList({
  badgeText = "Transparent Pricing",
  title = "Services & Price Menu",
  subtitle = "Clear, upfront service pricing tailored to your requirements with no hidden fees.",
  categories,
  services = [
    {
      id: "srv-1",
      name: "Initial Diagnostic Consultation",
      price: "$65",
      isStartingPrice: false,
      duration: "30 mins",
      description: "Thorough initial assessment, personalized review of requirements, and tailored action plan.",
      category: "Consulting",
      badge: "Popular",
    },
    {
      id: "srv-2",
      name: "Standard Full-Service Session",
      price: "$120",
      isStartingPrice: false,
      duration: "60 mins",
      description: "Comprehensive one-on-one session including diagnostic analysis and direct hands-on support.",
      category: "Treatment",
    },
    {
      id: "srv-3",
      name: "Specialized Deep-Dive Package",
      price: "$240",
      isStartingPrice: true,
      duration: "120 mins",
      description: "Intensive multi-hour focused engagement for complex projects or urgent turnaround requirements.",
      category: "Treatment",
      badge: "Comprehensive",
    },
    {
      id: "srv-4",
      name: "Follow-Up & Maintenance Check",
      price: "$45",
      isStartingPrice: false,
      duration: "20 mins",
      description: "Quick progress evaluation and ongoing calibration for established clients.",
      category: "Consulting",
    },
  ],
  footnote = "All prices include standard equipment and materials. Custom corporate packages available upon request.",
  bookingCtaText = "Book a Consultation",
  bookingCtaHref = "#contact",
  className,
}: ServicesPriceListProps) {
  const [activeCategory, setActiveCategory] = useState<string>("All")

  const availableCategories = categories || [
    "All",
    ...Array.from(new Set((services || []).map((s) => s.category).filter(Boolean) as string[])),
  ]

  const filteredServices = (services || []).filter((s) => {
    if (activeCategory === "All" || !s.category) return true
    return s.category.toLowerCase() === activeCategory.toLowerCase()
  })

  if (!services || services.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <Tag className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No services currently listed in the price menu.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="services-pricing" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center space-y-3 mb-12">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground max-w-xl mx-auto">{subtitle}</p>}
        </div>

        {/* Optional Category Switcher */}
        {availableCategories.length > 2 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
            {availableCategories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCategory(cat)}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                  activeCategory.toLowerCase() === cat.toLowerCase()
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {/* Services Price Card */}
        <Card className="border-border bg-card shadow-sm overflow-hidden">
          <CardContent className="p-0 divide-y divide-border/60">
            {filteredServices.map((service) => (
              <div
                key={service.id}
                className="p-6 hover:bg-muted/30 transition-colors flex flex-col sm:flex-row sm:items-baseline justify-between gap-4"
              >
                {/* Service Details */}
                <div className="space-y-1.5 flex-1 pr-4">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h3 className="font-bold text-foreground text-base sm:text-lg">{service.name}</h3>
                    {service.badge && (
                      <Badge className="bg-primary/10 text-primary hover:bg-primary/20 border-primary/20 text-[10px] py-0 px-2 font-medium">
                        {service.badge}
                      </Badge>
                    )}
                    {service.duration && (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-md">
                        <Clock className="h-3 w-3" />
                        {service.duration}
                      </span>
                    )}
                  </div>
                  {service.description && (
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-xl">
                      {service.description}
                    </p>
                  )}
                </div>

                {/* Price Display */}
                <div className="flex sm:flex-col items-baseline sm:items-end justify-between sm:justify-start shrink-0">
                  <div className="text-right">
                    {service.isStartingPrice && (
                      <span className="text-[11px] text-muted-foreground font-normal uppercase tracking-wider block">
                        from
                      </span>
                    )}
                    <span className="text-xl sm:text-2xl font-black text-primary tabular-nums">
                      {service.price}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Footnote & CTA */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          {footnote && <p className="text-center sm:text-left max-w-md">{footnote}</p>}
          {bookingCtaText && (
            <Button asChild size="sm" className="shrink-0 gap-1.5 font-semibold">
              <a href={bookingCtaHref}>
                {bookingCtaText}
                <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </Button>
          )}
        </div>
      </div>
    </section>
  )
}
