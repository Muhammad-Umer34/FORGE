// Interactive appointment date and time slot picker driven by dynamic availability schedules

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Calendar, Clock, CheckCircle2, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

export interface AppointmentSlotPickerProps {
  badgeText?: string
  title?: string
  subtitle?: string
  availability?: Record<string, string[]> // dateString -> array of time strings e.g. "2026-10-20": ["09:00 AM", "11:30 AM"]
  confirmButtonText?: string
  onSlotSelect?: (date: string, time: string) => void
  className?: string
}

const DEFAULT_AVAILABILITY: Record<string, string[]> = {
  "2026-10-20": ["09:00 AM", "11:00 AM", "02:00 PM", "04:30 PM"],
  "2026-10-21": ["10:00 AM", "01:00 PM", "03:30 PM"],
  "2026-10-22": ["09:30 AM", "11:30 AM", "02:30 PM", "05:00 PM"],
  "2026-10-23": ["08:30 AM", "10:30 AM", "01:30 PM"],
}

export function AppointmentSlotPicker({
  badgeText = "Real-time Availability",
  title = "Select an Appointment Slot",
  subtitle = "Choose your preferred appointment day and select an open time slot from the calendar below.",
  availability = DEFAULT_AVAILABILITY,
  confirmButtonText = "Confirm Selected Slot",
  onSlotSelect,
  className,
}: AppointmentSlotPickerProps) {
  const dates = Object.keys(availability || {})
  const [selectedDate, setSelectedDate] = useState<string>(dates[0] || "")
  const [selectedTime, setSelectedTime] = useState<string>("")
  const [isConfirmed, setIsConfirmed] = useState(false)

  const activeSlots = (availability && selectedDate ? availability[selectedDate] : []) || []

  const handleConfirm = () => {
    if (!selectedDate || !selectedTime) return
    setIsConfirmed(true)
    onSlotSelect?.(selectedDate, selectedTime)
  }

  if (dates.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <Calendar className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No appointment slots are currently open for booking.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="slot-picker" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
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
        </div>

        {isConfirmed ? (
          <Card className="max-w-md mx-auto p-8 border-primary/20 bg-card shadow-sm text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-bold text-foreground">Time Slot Reserved</h3>
            <p className="text-xs sm:text-sm text-muted-foreground">
              You selected <strong className="text-foreground">{selectedDate}</strong> at{" "}
              <strong className="text-foreground">{selectedTime}</strong>.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsConfirmed(false)
                setSelectedTime("")
              }}
            >
              Choose a Different Time
            </Button>
          </Card>
        ) : (
          <Card className="border-border bg-card shadow-sm overflow-hidden p-6 sm:p-8 space-y-8">
            {/* Step 1: Date Buttons Strip */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <Calendar className="h-4 w-4 text-primary" />
                <span>Step 1: Choose Available Date</span>
              </div>
              <div className="flex gap-2.5 overflow-x-auto pb-2">
                {dates.map((d) => {
                  const isSelected = selectedDate === d
                  const slotsCount = availability[d]?.length || 0
                  return (
                    <button
                      key={d}
                      type="button"
                      onClick={() => {
                        setSelectedDate(d)
                        setSelectedTime("")
                      }}
                      className={cn(
                        "p-3 rounded-xl border text-center min-w-[110px] shrink-0 transition-all",
                        isSelected
                          ? "bg-primary text-primary-foreground border-primary shadow-xs"
                          : "bg-muted/30 text-foreground border-border hover:bg-muted"
                      )}
                    >
                      <div className="text-xs font-bold">{d}</div>
                      <div className={cn("text-[10px] mt-0.5", isSelected ? "text-primary-foreground/80" : "text-muted-foreground")}>
                        {slotsCount} open slots
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Step 2: Time Slots Grid */}
            <div className="space-y-3 pt-4 border-t border-border/60">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <Clock className="h-4 w-4 text-primary" />
                <span>Step 2: Choose Time Slot for {selectedDate}</span>
              </div>

              {activeSlots.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4">No open slots available on this date.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {activeSlots.map((time) => {
                    const isSelected = selectedTime === time
                    return (
                      <button
                        key={time}
                        type="button"
                        onClick={() => setSelectedTime(time)}
                        className={cn(
                          "py-3 px-4 rounded-xl border text-sm font-semibold transition-all text-center",
                          isSelected
                            ? "bg-primary text-primary-foreground border-primary shadow-xs"
                            : "bg-card text-foreground border-border hover:border-primary/40 hover:bg-muted/40"
                        )}
                      >
                        {time}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Selection Confirmation Bar */}
            <div className="pt-6 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-xs text-muted-foreground text-center sm:text-left">
                {selectedDate && selectedTime ? (
                  <span>
                    Selected: <strong className="text-foreground">{selectedDate}</strong> at{" "}
                    <strong className="text-primary">{selectedTime}</strong>
                  </span>
                ) : (
                  <span>Please choose both a date and a time slot above.</span>
                )}
              </div>

              <Button
                onClick={handleConfirm}
                disabled={!selectedDate || !selectedTime}
                className="w-full sm:w-auto px-6 gap-2"
              >
                {confirmButtonText}
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        )}
      </div>
    </section>
  )
}
