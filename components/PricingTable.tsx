// Tiered pricing cards with billing interval toggle, feature checklists, highlighted popular tier, and CTA buttons

"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Check, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export interface PricingPlan {
  name: string
  price: string
  yearlyPrice?: string
  description: string
  isPopular?: boolean
  features: string[]
  ctaText: string
  ctaHref?: string
  onCtaClick?: () => void
}

export interface PricingTableProps {
  badgeText?: string
  title?: string
  subtitle?: string
  enableAnnualToggle?: boolean
  annualDiscountBadge?: string
  plans?: PricingPlan[]
  className?: string
}

export function PricingTable({
  badgeText = "Simple, Predictable Pricing",
  title = "Choose the Right Plan for Your Scale",
  subtitle = "Start for free and scale smoothly as your applications, generation quota, and traffic expand.",
  enableAnnualToggle = true,
  annualDiscountBadge = "Save 20%",
  plans = [
    {
      name: "Starter",
      price: "$0",
      yearlyPrice: "$0",
      description: "Perfect for indie hackers, students, and rapid hobby prototyping.",
      features: [
        "Up to 15 site generations/month",
        "Standard WebContainers preview engine",
        "Export clean Next.js/Tailwind source code",
        "Community Discord support",
      ],
      ctaText: "Start Building Free",
      ctaHref: "#starter",
    },
    {
      name: "Professional",
      price: "$29",
      yearlyPrice: "$23",
      description: "Ideal for freelance developers, agencies, and production apps.",
      isPopular: true,
      features: [
        "Unlimited site generations",
        "Instant turbo WebContainers execution",
        "Custom branding & domain publishing",
        "All 12+ Section Library components",
        "Priority API access & 24/7 support",
      ],
      ctaText: "Get Pro Access",
      ctaHref: "#pro",
    },
    {
      name: "Enterprise",
      price: "$99",
      yearlyPrice: "$79",
      description: "Dedicated infrastructure, multi-seat teams, and custom models.",
      features: [
        "Everything in Professional",
        "Dedicated isolated compute instances",
        "Custom LLM fine-tuning on brand guidelines",
        "SLA & Dedicated Account Manager",
        "SSO & Role-based team permissions",
      ],
      ctaText: "Contact Sales",
      ctaHref: "#enterprise",
    },
  ],
  className,
}: PricingTableProps) {
  const [isYearly, setIsYearly] = useState(false)

  return (
    <section
      id="pricing"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-8">
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

          {/* Billing Switcher Toggle */}
          {enableAnnualToggle && (
            <div className="pt-4 flex items-center justify-center gap-3">
              <span
                className={cn(
                  "text-xs sm:text-sm font-medium cursor-pointer",
                  !isYearly ? "text-foreground font-semibold" : "text-muted-foreground"
                )}
                onClick={() => setIsYearly(false)}
              >
                Monthly Billing
              </span>

              <button
                type="button"
                onClick={() => setIsYearly(!isYearly)}
                className={cn(
                  "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isYearly ? "bg-primary" : "bg-muted"
                )}
              >
                <span
                  className={cn(
                    "pointer-events-none inline-block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition duration-200 ease-in-out",
                    isYearly ? "translate-x-5" : "translate-x-0"
                  )}
                />
              </button>

              <span
                className={cn(
                  "text-xs sm:text-sm font-medium cursor-pointer flex items-center gap-1.5",
                  isYearly ? "text-foreground font-semibold" : "text-muted-foreground"
                )}
                onClick={() => setIsYearly(true)}
              >
                Annual Billing
                {annualDiscountBadge && (
                  <Badge variant="secondary" className="text-[10px] bg-primary/10 text-primary border-primary/20">
                    {annualDiscountBadge}
                  </Badge>
                )}
              </span>
            </div>
          )}
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch pt-4">
          {plans.map((plan, idx) => {
            const displayPrice = isYearly && plan.yearlyPrice ? plan.yearlyPrice : plan.price

            return (
              <Card
                key={idx}
                className={cn(
                  "flex flex-col relative transition-all duration-200 rounded-2xl",
                  plan.isPopular
                    ? "border-2 border-primary shadow-xl scale-100 md:scale-105 z-10 bg-card"
                    : "border-border shadow-sm hover:shadow-md bg-card/60"
                )}
              >
                {plan.isPopular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground gap-1 px-3 py-1 text-xs shadow">
                      <Sparkles className="h-3 w-3" /> Most Popular
                    </Badge>
                  </div>
                )}

                <CardHeader className="p-6 sm:p-8 pb-4">
                  <CardTitle className="text-xl font-bold">{plan.name}</CardTitle>
                  <CardDescription className="text-xs sm:text-sm min-h-[40px] mt-1">
                    {plan.description}
                  </CardDescription>

                  <div className="pt-4 flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold tracking-tight text-foreground">
                      {displayPrice}
                    </span>
                    <span className="text-xs text-muted-foreground font-medium">
                      / month {isYearly && "(billed annually)"}
                    </span>
                  </div>
                </CardHeader>

                <CardContent className="p-6 sm:p-8 pt-2 flex-1 space-y-4">
                  <div className="text-xs font-semibold text-foreground uppercase tracking-wider">
                    Included Features
                  </div>
                  <ul className="space-y-3 text-sm text-muted-foreground">
                    {plan.features.map((feat, fIdx) => (
                      <li key={fIdx} className="flex items-start gap-2.5">
                        <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                        <span className="leading-tight text-xs sm:text-sm text-foreground/90">
                          {feat}
                        </span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter className="p-6 sm:p-8 pt-0">
                  <Button
                    variant={plan.isPopular ? "default" : "outline"}
                    className="w-full font-medium"
                    onClick={plan.onCtaClick}
                    asChild={!plan.onCtaClick && Boolean(plan.ctaHref)}
                  >
                    {plan.onCtaClick ? (
                      plan.ctaText
                    ) : (
                      <a href={plan.ctaHref}>{plan.ctaText}</a>
                    )}
                  </Button>
                </CardFooter>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
