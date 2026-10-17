// Features & Services Grid: Responsive icon cards highlighting key business capabilities, services, or product features

"use client"

import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  Sparkles, 
  Zap, 
  ShieldCheck, 
  Clock, 
  Layers, 
  HeartHandshake, 
  CheckCircle2,
  LucideIcon 
} from "lucide-react"
import { cn } from "@/lib/utils"

export interface FeatureItem {
  id?: string
  title: string
  description: string
  badge?: string
  iconName?: string
}

export interface FeaturesGridProps {
  badgeText?: string
  title?: string
  subtitle?: string
  features?: FeatureItem[]
  columns?: 2 | 3 | 4
  className?: string
}

// Icon mapping dictionary
const ICON_MAP: Record<string, LucideIcon> = {
  zap: Zap,
  shield: ShieldCheck,
  clock: Clock,
  layers: Layers,
  heart: HeartHandshake,
  sparkles: Sparkles,
}

export function FeaturesGrid({
  badgeText = "Services & Features",
  title = "Core Capabilities Designed for Real Impact",
  subtitle = "Explore our comprehensive suite of tailored services and specialized solutions built to exceed expectations.",
  features = [
    {
      id: "f1",
      title: "Comprehensive Consultations",
      description: "In-depth diagnostic assessment, personalized treatment roadmap, and transparent recommendations tailored to your goals.",
      badge: "Core Service",
      iconName: "sparkles",
    },
    {
      id: "f2",
      title: "Rapid Turnaround & Booking",
      description: "Streamlined scheduling with real-time slot availability, instant confirmation alerts, and zero waiting room delays.",
      badge: "Fast & Reliable",
      iconName: "clock",
    },
    {
      id: "f3",
      title: "Certified Quality & Safety",
      description: "Operating under strict clinical standards, advanced sanitization, and verified practitioner accreditations.",
      badge: "Guaranteed",
      iconName: "shield",
    },
    {
      id: "f4",
      title: "Modern Tech & Equipment",
      description: "State-of-the-art digital imaging, painless procedures, and modern instruments delivering superior precision.",
      badge: "State-of-the-Art",
      iconName: "zap",
    },
    {
      id: "f5",
      title: "Dedicated Aftercare Support",
      description: "Continuous follow-up check-ins, direct specialist messaging, and emergency assistance whenever you need it.",
      badge: "24/7 Support",
      iconName: "heart",
    },
    {
      id: "f6",
      title: "Transparent & Flexible Plans",
      description: "Clear upfront pricing with no hidden charges, flexible payment plans, and direct insurance billing assistance.",
      badge: "No Surprises",
      iconName: "layers",
    },
  ],
  columns = 3,
  className,
}: FeaturesGridProps) {
  const gridColsClass = {
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  }[columns]

  return (
    <section
      id="features"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
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

        {/* Features Grid */}
        <div className={cn("grid gap-6 sm:gap-8", gridColsClass)}>
          {features.map((item, idx) => {
            const IconComponent = (item.iconName && ICON_MAP[item.iconName.toLowerCase()]) || CheckCircle2

            return (
              <Card
                key={item.id || idx}
                className="group relative border-border bg-card/60 backdrop-blur shadow-sm hover:shadow-md hover:border-primary/40 transition-all duration-300 rounded-2xl p-6 sm:p-7 flex flex-col justify-between"
              >
                <div className="space-y-4">
                  {/* Icon & Badge */}
                  <div className="flex items-center justify-between">
                    <div className="h-11 w-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center border border-primary/20 group-hover:scale-105 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                      <IconComponent className="h-5 w-5" />
                    </div>
                    {item.badge && (
                      <span className="text-[11px] font-medium text-muted-foreground bg-muted/60 px-2.5 py-0.5 rounded-full border border-border/60">
                        {item.badge}
                      </span>
                    )}
                  </div>

                  {/* Title & Description */}
                  <div className="space-y-2">
                    <h3 className="font-semibold text-lg text-foreground group-hover:text-primary transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
