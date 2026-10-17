// Weekly operating hours schedule with day-of-week highlighting, lunch break support, and client-time open/closed status

"use client"

import React, { useMemo } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Clock, Calendar, CheckCircle2, XCircle, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface DaySchedule {
  day: string
  dayIndex: number // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  isClosed?: boolean
  openTime?: string // 24h format "HH:MM", e.g., "09:00"
  closeTime?: string // 24h format "HH:MM", e.g., "18:00"
  displayHours?: string // e.g., "9:00 AM - 6:00 PM"
  lunchBreak?: {
    start: string // "13:00"
    end: string // "14:00"
    display?: string // "1:00 PM - 2:00 PM"
  }
  note?: string
}

export interface BusinessHoursProps {
  badgeText?: string
  title?: string
  subtitle?: string
  schedule?: DaySchedule[]
  timezoneNote?: string
  emergencyNote?: string
  className?: string
}

const DEFAULT_SCHEDULE: DaySchedule[] = [
  { day: "Monday", dayIndex: 1, openTime: "09:00", closeTime: "18:00", displayHours: "9:00 AM – 6:00 PM" },
  {
    day: "Tuesday",
    dayIndex: 2,
    openTime: "09:00",
    closeTime: "18:00",
    displayHours: "9:00 AM – 6:00 PM",
    lunchBreak: { start: "13:00", end: "14:00", display: "1:00 PM – 2:00 PM" },
  },
  { day: "Wednesday", dayIndex: 3, openTime: "09:00", closeTime: "18:00", displayHours: "9:00 AM – 6:00 PM" },
  { day: "Thursday", dayIndex: 4, openTime: "09:00", closeTime: "18:00", displayHours: "9:00 AM – 6:00 PM" },
  { day: "Friday", dayIndex: 5, openTime: "09:00", closeTime: "17:00", displayHours: "9:00 AM – 5:00 PM" },
  { day: "Saturday", dayIndex: 6, openTime: "10:00", closeTime: "15:00", displayHours: "10:00 AM – 3:00 PM" },
  { day: "Sunday", dayIndex: 0, isClosed: true, displayHours: "Closed" },
]

function parseTimeToMinutes(timeStr?: string): number | null {
  if (!timeStr) return null
  const [h, m] = timeStr.split(":").map(Number)
  if (isNaN(h) || isNaN(m)) return null
  return h * 60 + m
}

export function BusinessHours({
  badgeText = "Opening Hours",
  title = "Business Hours & Availability",
  subtitle = "Our weekly schedule of operation. Stop by or get in touch during these hours.",
  schedule = DEFAULT_SCHEDULE,
  timezoneNote = "Times shown in your local timezone.",
  emergencyNote,
  className,
}: BusinessHoursProps) {
  // Determine if open right now based on client local time
  const status = useMemo(() => {
    if (typeof window === "undefined") return { isOpen: false, isLunch: false, currentDayIdx: -1 }
    const now = new Date()
    const currentDayIdx = now.getDay()
    const currentMinutes = now.getHours() * 60 + now.getMinutes()

    const todayEntry = schedule.find((s) => s.dayIndex === currentDayIdx)
    if (!todayEntry || todayEntry.isClosed) {
      return { isOpen: false, isLunch: false, currentDayIdx }
    }

    const openMin = parseTimeToMinutes(todayEntry.openTime)
    const closeMin = parseTimeToMinutes(todayEntry.closeTime)

    if (openMin === null || closeMin === null) {
      return { isOpen: false, isLunch: false, currentDayIdx }
    }

    // Check lunch break
    if (todayEntry.lunchBreak) {
      const lunchStart = parseTimeToMinutes(todayEntry.lunchBreak.start)
      const lunchEnd = parseTimeToMinutes(todayEntry.lunchBreak.end)
      if (lunchStart !== null && lunchEnd !== null) {
        if (currentMinutes >= lunchStart && currentMinutes < lunchEnd) {
          return { isOpen: false, isLunch: true, currentDayIdx }
        }
      }
    }

    const isOpen = currentMinutes >= openMin && currentMinutes < closeMin
    return { isOpen, isLunch: false, currentDayIdx }
  }, [schedule])

  if (!schedule || schedule.length === 0) {
    return null
  }

  return (
    <section id="hours" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center space-y-3 mb-10">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground max-w-xl mx-auto">{subtitle}</p>}

          {/* Current Status Pill */}
          <div className="pt-2 flex justify-center">
            {status.isOpen ? (
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Open Now
              </div>
            ) : status.isLunch ? (
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                <Clock className="h-3.5 w-3.5" />
                Closed for Lunch Break
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border">
                <span className="h-2 w-2 rounded-full bg-muted-foreground/60" />
                Currently Closed
              </div>
            )}
          </div>
        </div>

        {/* Schedule Table Card */}
        <Card className="border-border bg-card shadow-sm overflow-hidden">
          <CardContent className="p-0">
            <div className="divide-y divide-border/60">
              {schedule.map((item) => {
                const isToday = item.dayIndex === status.currentDayIdx
                return (
                  <div
                    key={item.day}
                    className={cn(
                      "px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 transition-colors",
                      isToday ? "bg-primary/5 font-medium" : "hover:bg-muted/30"
                    )}
                  >
                    {/* Day Column */}
                    <div className="flex items-center gap-3">
                      <div className="w-28 flex items-center gap-2 text-sm text-foreground">
                        <span>{item.day}</span>
                        {isToday && (
                          <Badge variant="secondary" className="text-[10px] uppercase tracking-wider py-0 px-1.5 font-bold">
                            Today
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Hours Column */}
                    <div className="flex flex-col sm:items-end text-sm">
                      {item.isClosed ? (
                        <span className="text-muted-foreground font-medium flex items-center gap-1.5 text-xs">
                          <XCircle className="h-3.5 w-3.5 opacity-60" />
                          Closed
                        </span>
                      ) : (
                        <span className="text-foreground font-semibold flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5 text-primary opacity-80" />
                          {item.displayHours || `${item.openTime || "09:00"} – ${item.closeTime || "18:00"}`}
                        </span>
                      )}

                      {/* Lunch Break Note */}
                      {item.lunchBreak && !item.isClosed && (
                        <span className="text-xs text-muted-foreground mt-0.5">
                          Lunch: {item.lunchBreak.display || `${item.lunchBreak.start} – ${item.lunchBreak.end}`}
                        </span>
                      )}

                      {/* Extra Note */}
                      {item.note && <span className="text-xs text-primary/80 mt-0.5">{item.note}</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Footer Notes */}
        {(timezoneNote || emergencyNote) && (
          <div className="mt-6 space-y-1 text-center text-xs text-muted-foreground">
            {timezoneNote && <p>{timezoneNote}</p>}
            {emergencyNote && (
              <p className="flex items-center justify-center gap-1.5 text-foreground font-medium pt-1">
                <AlertCircle className="h-3.5 w-3.5 text-primary" />
                {emergencyNote}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
