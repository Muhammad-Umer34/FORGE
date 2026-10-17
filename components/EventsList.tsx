// Community events and scheduled activities list with calendar date badges, venue locations, RSVP links, and past-event status handling

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Calendar, Clock, MapPin, ArrowRight, ExternalLink, CalendarDays } from "lucide-react"
import { cn } from "@/lib/utils"

export interface EventItem {
  id: string
  title: string
  date: string // e.g. "October 24, 2026"
  month?: string // e.g. "OCT"
  day?: string // e.g. "24"
  time: string // e.g. "6:00 PM – 8:30 PM"
  location: string // e.g. "Community Center Hall, Room 102"
  description?: string
  category?: string
  link?: {
    label: string
    href: string
  }
  isPast?: boolean
  isoDate?: string // e.g. "2026-10-24"
}

export interface EventsListProps {
  badgeText?: string
  title?: string
  subtitle?: string
  events?: EventItem[]
  hidePastEvents?: boolean
  className?: string
}

export function EventsList({
  badgeText = "Upcoming Gatherings",
  title = "Events, Workshops & Gatherings",
  subtitle = "Join us in person or online for upcoming workshops, community showcases, and seasonal events.",
  events = [
    {
      id: "ev-1",
      title: "Community Tasting & Sourdough Workshop",
      date: "October 24, 2026",
      month: "OCT",
      day: "24",
      time: "10:00 AM – 1:00 PM",
      location: "Main Bakery Hearth, 123 Business Way",
      description: "Hands-on fermentation masterclass covering starter maintenance, dough folding, and woodfire baking.",
      category: "Workshop",
      link: { label: "RSVP Now", href: "#" },
      isPast: false,
    },
    {
      id: "ev-2",
      title: "Autumn Artisan Vendor Showcase",
      date: "November 14, 2026",
      month: "NOV",
      day: "14",
      time: "11:00 AM – 5:00 PM",
      location: "Downtown Plaza Square",
      description: "A collaborative weekend fair showcasing handcrafted goods, locally roasted coffee, and live acoustic music.",
      category: "Community",
      link: { label: "Learn More", href: "#" },
      isPast: false,
    },
    {
      id: "ev-3",
      title: "Summer Welcome & Patio Gathering",
      date: "August 12, 2026",
      month: "AUG",
      day: "12",
      time: "6:00 PM – 9:00 PM",
      location: "Garden Patio",
      description: "An evening gathering celebrating the start of the summer season with friends and neighbors.",
      category: "Social",
      isPast: true,
    },
  ],
  hidePastEvents = false,
  className,
}: EventsListProps) {
  // Determine past state for each event
  const processedEvents = (events || [])
    .map((ev) => {
      let isPastEvent = ev.isPast
      if (isPastEvent === undefined && ev.isoDate) {
        isPastEvent = new Date(ev.isoDate).getTime() < new Date().setHours(0, 0, 0, 0)
      }
      return { ...ev, isPast: Boolean(isPastEvent) }
    })
    .filter((ev) => !hidePastEvents || !ev.isPast)

  if (!events || events.length === 0 || processedEvents.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <CalendarDays className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No scheduled events at this time. Check back soon!</p>
        </div>
      </section>
    )
  }

  return (
    <section id="events" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-3xl mx-auto text-center space-y-3 mb-12">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground">{subtitle}</p>}
        </div>

        {/* Events Cards List */}
        <div className="space-y-4">
          {processedEvents.map((item) => {
            const displayMonth = item.month || item.date.slice(0, 3).toUpperCase()
            const displayDay = item.day || item.date.match(/\d+/)?.[0] || ""

            return (
              <Card
                key={item.id}
                className={cn(
                  "border-border bg-card transition-all duration-200 overflow-hidden",
                  item.isPast ? "opacity-60 bg-muted/20" : "hover:border-primary/40 hover:shadow-sm"
                )}
              >
                <CardContent className="p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
                  {/* Left: Date Badge + Details */}
                  <div className="flex items-start gap-5">
                    {/* Date Block */}
                    <div
                      className={cn(
                        "h-16 w-16 rounded-xl flex flex-col items-center justify-center shrink-0 border text-center shadow-xs",
                        item.isPast
                          ? "bg-muted border-border text-muted-foreground"
                          : "bg-primary/10 border-primary/20 text-primary"
                      )}
                    >
                      <span className="text-[11px] font-bold tracking-wider leading-none">{displayMonth}</span>
                      <span className="text-2xl font-black leading-tight">{displayDay}</span>
                    </div>

                    {/* Meta & Info */}
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        {item.category && (
                          <Badge variant="secondary" className="text-[10px] py-0 px-2 font-medium">
                            {item.category}
                          </Badge>
                        )}
                        {item.isPast && (
                          <Badge variant="outline" className="text-[10px] py-0 px-2 text-muted-foreground">
                            Past Event
                          </Badge>
                        )}
                      </div>

                      <h3 className="font-bold text-lg text-foreground leading-snug">{item.title}</h3>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground pt-0.5">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5 text-primary" />
                          {item.time}
                        </span>
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5 text-primary" />
                          {item.location}
                        </span>
                      </div>

                      {item.description && (
                        <p className="text-xs sm:text-sm text-muted-foreground pt-1 max-w-xl leading-relaxed">
                          {item.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Right: Action Button */}
                  {item.link && !item.isPast && (
                    <div className="self-end sm:self-center shrink-0">
                      <Button asChild size="sm" className="gap-1.5">
                        <a href={item.link.href}>
                          {item.link.label}
                          <ArrowRight className="h-3.5 w-3.5" />
                        </a>
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
