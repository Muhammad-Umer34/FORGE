// Process / How It Works: Numbered step-by-step visual workflow for bookings, consults, and deliveries

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Calendar, UserCheck, Sparkles, CheckCircle, ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ProcessStep {
  stepNumber: number | string
  title: string
  description: string
  detail?: string
}

export interface ProcessStepsProps {
  badgeText?: string
  title?: string
  subtitle?: string
  steps?: ProcessStep[]
  className?: string
}

export function ProcessSteps({
  badgeText = "How It Works",
  title = "Simple, Transparent 3-Step Journey",
  subtitle = "We make booking and consultation entirely effortless. Here is exactly what happens when you work with us.",
  steps = [
    {
      stepNumber: "01",
      title: "Select Service & Time Slot",
      description: "Browse our comprehensive service menu, choose your preferred specialist, and select a convenient calendar slot.",
      detail: "Takes under 2 minutes",
    },
    {
      stepNumber: "02",
      title: "Confirm Your Reservation",
      description: "Provide key details and any specific preferences. Receive an instant SMS and email confirmation with calendar sync.",
      detail: "Instant confirmation",
    },
    {
      stepNumber: "03",
      title: "Experience Personalized Care",
      description: "Arrive at your appointment with zero waiting room hassle. Enjoy personalized attention, care, and follow-up support.",
      detail: "Continuous follow-up",
    },
  ],
  className,
}: ProcessStepsProps) {
  return (
    <section
      id="process"
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

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative items-stretch">
          {steps.map((step, idx) => (
            <div
              key={idx}
              className="relative p-6 sm:p-8 rounded-2xl border border-border bg-card/60 backdrop-blur shadow-sm hover:border-primary/40 transition-all duration-300 flex flex-col justify-between group"
            >
              <div>
                {/* Step Number Badge */}
                <div className="flex items-center justify-between mb-6">
                  <div className="h-12 w-12 rounded-xl bg-primary/10 border border-primary/20 text-primary font-black text-xl flex items-center justify-center group-hover:bg-primary group-hover:text-primary-foreground group-hover:scale-105 transition-all duration-300">
                    {step.stepNumber}
                  </div>
                  {idx < steps.length - 1 && (
                    <ArrowRight className="hidden md:block h-5 w-5 text-muted-foreground/40 -mr-4" />
                  )}
                </div>

                <h3 className="font-semibold text-lg text-foreground mb-2 group-hover:text-primary transition-colors">
                  {step.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </div>

              {step.detail && (
                <div className="mt-6 pt-4 border-t border-border/50 text-xs font-medium text-primary flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" />
                  {step.detail}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
