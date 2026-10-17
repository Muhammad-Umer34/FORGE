// Customer testimonials and social proof cards with star ratings, client quotes, avatars, names, and company roles

"use client"

import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Star, Quote } from "lucide-react"
import { cn } from "@/lib/utils"

export interface TestimonialItem {
  quote: string
  author: string
  role: string
  company?: string
  avatarUrl?: string
  rating?: number
}

export interface TestimonialsProps {
  badgeText?: string
  title?: string
  subtitle?: string
  items?: TestimonialItem[]
  className?: string
}

export function Testimonials({
  badgeText = "Social Proof & Reviews",
  title = "Loved by Hundreds of Fast-Moving Engineering Teams",
  subtitle = "See how developers, startup founders, and agency leads use FORGE to build, preview, and deploy web applications 10x faster.",
  items = [
    {
      quote:
        "FORGE completely transformed how we pitch web concepts to clients. What used to take two weeks of mockups and frontend staging now happens in two minutes with live browser preview.",
      author: "Sarah Jenkins",
      role: "VP of Product",
      company: "Apex Digital Labs",
      avatarUrl: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=200&q=80",
      rating: 5,
    },
    {
      quote:
        "The WebContainers engine combined with shadcn/ui components produces shockingly clean, idiomatic Next.js code. Zero lock-in, pristine TypeScript, and instant builds.",
      author: "David Chen",
      role: "Principal Architect",
      company: "StackFlow Systems",
      avatarUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80",
      rating: 5,
    },
    {
      quote:
        "As a non-technical founder, I was able to build and iterate our entire SaaS marketing site and booking flow in one afternoon without hiring a contractor.",
      author: "Elena Rostova",
      role: "Founder & CEO",
      company: "Solaria Health",
      avatarUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80",
      rating: 5,
    },
  ],
  className,
}: TestimonialsProps) {
  return (
    <section
      id="testimonials"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-12">
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

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 items-stretch">
          {items.map((item, idx) => {
            const rating = item.rating || 5

            return (
              <Card
                key={idx}
                className="flex flex-col justify-between border-border bg-card/60 backdrop-blur shadow-sm hover:shadow-md transition-shadow rounded-2xl p-6 sm:p-8"
              >
                <CardContent className="p-0 space-y-4">
                  {/* Star Ratings */}
                  <div className="flex items-center gap-1 text-amber-500">
                    {Array.from({ length: 5 }).map((_, sIdx) => (
                      <Star
                        key={sIdx}
                        className={cn(
                          "h-4 w-4 fill-current",
                          sIdx < rating ? "text-amber-500" : "text-muted-foreground/30"
                        )}
                      />
                    ))}
                  </div>

                  {/* Quote */}
                  <div className="relative">
                    <p className="text-sm sm:text-base text-foreground/90 leading-relaxed italic">
                      "{item.quote}"
                    </p>
                  </div>
                </CardContent>

                {/* Author Info Footer */}
                <div className="pt-6 mt-6 border-t border-border/60 flex items-center gap-3">
                  {item.avatarUrl ? (
                    <img
                      src={item.avatarUrl}
                      alt={item.author}
                      className="h-11 w-11 rounded-full object-cover border border-border"
                    />
                  ) : (
                    <div className="h-11 w-11 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
                      {item.author.charAt(0)}
                    </div>
                  )}

                  <div>
                    <h4 className="font-semibold text-sm text-foreground">
                      {item.author}
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      {item.role} {item.company && `• ${item.company}`}
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
