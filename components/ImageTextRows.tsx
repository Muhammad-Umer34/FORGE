// Alternating two-column editorial content rows with responsive single-column mobile stacking

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CheckCircle2, ArrowRight, Layers } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ImageTextRowItem {
  id: string
  title: string
  description: string
  imageUrl: string
  imageAlt?: string
  badge?: string
  features?: string[]
  actionLink?: {
    label: string
    href: string
  }
}

export interface ImageTextRowsProps {
  badgeText?: string
  title?: string
  subtitle?: string
  rows?: ImageTextRowItem[]
  className?: string
}

export function ImageTextRows({
  badgeText = "Why Choose Us",
  title = "Built with Care, Rooted in Quality",
  subtitle = "Discover the thoughtful details that distinguish our craft, philosophy, and client commitment.",
  rows = [
    {
      id: "row-1",
      badge: "Sourcing",
      title: "Direct Regional Farmer Partnerships",
      description: "We work directly with sustainable Pacific Northwest agricultural growers, ensuring our organic flours and butter are milled fresh each week.",
      imageUrl: "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1000&q=80",
      imageAlt: "Organic heirloom wheat field",
      features: ["100% Certified Organic grains", "Zero artificial preservatives or bleaches", "Full farm-to-table traceability"],
      actionLink: { label: "Learn About Our Sourcing", href: "#about" },
    },
    {
      id: "row-2",
      badge: "Technique",
      title: "Traditional 36-Hour Cold Proofing",
      description: "Time is our most valuable ingredient. Long, slow cold fermentation unlocks deep, complex flavor profiles while making each loaf significantly gentler on digestion.",
      imageUrl: "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=1000&q=80",
      imageAlt: "Slow fermentation bread dough folding",
      features: ["Wild sourdough natural yeast culture", "Traditional granite stone baking hearth", "Baked fresh every morning at dawn"],
      actionLink: { label: "View Our Baking Process", href: "#process" },
    },
    {
      id: "row-3",
      badge: "Community",
      title: "A Welcoming Neighborhood Gathering Place",
      description: "More than just a bakery, our cafe is designed as a warm meeting spot where community members connect over warm espresso and fresh pastries.",
      imageUrl: "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1000&q=80",
      imageAlt: "Community gathering at bakery cafe",
      features: ["Complimentary high-speed WiFi", "Dog-friendly sunlit patio seating", "Weekend acoustic music sessions"],
    },
  ],
  className,
}: ImageTextRowsProps) {
  if (!rows || rows.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <Layers className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No content rows available.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="features-editorial" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-20">
        {/* Header */}
        <div className="max-w-3xl mx-auto text-center space-y-3">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground">{subtitle}</p>}
        </div>

        {/* Editorial Rows */}
        <div className="space-y-16 sm:space-y-24">
          {rows.map((row, idx) => {
            const isReversed = idx % 2 === 1

            return (
              <div
                key={row.id}
                className={cn(
                  "flex flex-col gap-10 lg:gap-16 items-center",
                  isReversed ? "lg:flex-row-reverse" : "lg:flex-row"
                )}
              >
                {/* Visual Image Column */}
                <div className="w-full lg:w-1/2">
                  <div className="relative aspect-[16/11] rounded-2xl overflow-hidden bg-muted border border-border shadow-md">
                    <img
                      src={row.imageUrl}
                      alt={row.imageAlt || row.title}
                      className="h-full w-full object-cover"
                    />
                  </div>
                </div>

                {/* Text Description Column */}
                <div className="w-full lg:w-1/2 space-y-5">
                  {row.badge && (
                    <Badge variant="secondary" className="text-xs font-semibold px-2.5 py-0.5">
                      {row.badge}
                    </Badge>
                  )}

                  <h3 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight leading-snug">
                    {row.title}
                  </h3>

                  <p className="text-base text-muted-foreground leading-relaxed">
                    {row.description}
                  </p>

                  {/* Checklist Items */}
                  {row.features && row.features.length > 0 && (
                    <ul className="space-y-2.5 pt-2">
                      {row.features.map((feat, fIdx) => (
                        <li key={fIdx} className="flex items-start gap-2.5 text-sm text-foreground">
                          <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Optional CTA */}
                  {row.actionLink && (
                    <div className="pt-2">
                      <Button asChild variant="outline" className="gap-2">
                        <a href={row.actionLink.href}>
                          {row.actionLink.label}
                          <ArrowRight className="h-4 w-4" />
                        </a>
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
