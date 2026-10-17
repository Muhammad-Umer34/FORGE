// Service booking and appointment reservation form with date selection, service options, guest details, and booking confirmation

"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Calendar, Clock, CheckCircle2, User, Mail, Phone, CalendarCheck, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface BookingServiceOption {
  id: string
  name: string
  duration: string
  price: string
  description?: string
}

export interface BookingData {
  serviceId: string
  serviceName: string
  date: string
  time: string
  fullName: string
  email: string
  phone: string
  notes?: string
}

export interface BookingFormProps {
  badgeText?: string
  title?: string
  subtitle?: string
  services?: BookingServiceOption[]
  timeSlots?: string[]
  submitButtonText?: string
  onSubmit?: (data: BookingData) => Promise<void> | void
  successMessage?: string
  className?: string
}

export function BookingForm({
  badgeText = "Reserve an Appointment",
  title = "Book a Consultation with Our Specialists",
  subtitle = "Select your desired service, pick a date and time slot, and confirm your appointment instantly.",
  services = [
    {
      id: "consultation-exam",
      name: "Initial Examination & Consultation",
      duration: "45 mins",
      price: "$90",
      description: "Comprehensive initial consultation, diagnostic checkup, and personalized treatment plan.",
    },
    {
      id: "standard-session",
      name: "Comprehensive Treatment Session",
      duration: "60 mins",
      price: "$180",
      description: "Thorough care session tailored to your specific health and service requirements.",
    },
    {
      id: "followup-checkup",
      name: "Follow-up & Preventive Checkup",
      duration: "30 mins",
      price: "Free",
      description: "Quick follow-up evaluation and progress check.",
    },
  ],
  timeSlots = ["09:00 AM", "11:00 AM", "02:00 PM", "04:30 PM", "06:00 PM"],
  submitButtonText = "Confirm Reservation",
  onSubmit,
  successMessage = "Your appointment has been successfully scheduled! A calendar invite has been sent to your email.",
  className,
}: BookingFormProps) {
  const [selectedServiceId, setSelectedServiceId] = useState(services[0]?.id || "")
  const [selectedDate, setSelectedDate] = useState("")
  const [selectedTime, setSelectedTime] = useState(timeSlots[0] || "")
  const [customer, setCustomer] = useState({
    fullName: "",
    email: "",
    phone: "",
    notes: "",
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isConfirmed, setIsConfirmed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedService = services.find((s) => s.id === selectedServiceId) || services[0]

  const handleBooking = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!selectedServiceId || !selectedDate || !selectedTime || !customer.fullName || !customer.email) {
      setError("Please complete all required fields (Service, Date, Time, Name, Email).")
      return
    }

    try {
      setIsSubmitting(true)
      const data: BookingData = {
        serviceId: selectedService.id,
        serviceName: selectedService.name,
        date: selectedDate,
        time: selectedTime,
        fullName: customer.fullName,
        email: customer.email,
        phone: customer.phone,
        notes: customer.notes,
      }

      if (onSubmit) {
        await onSubmit(data)
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800))
      }

      setIsConfirmed(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to book. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section
      id="booking"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-10">
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

        {/* Confirmation State */}
        {isConfirmed ? (
          <Card className="max-w-xl mx-auto border-emerald-500/30 bg-emerald-500/5 shadow-lg p-8 text-center space-y-4">
            <div className="h-16 w-16 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center mx-auto">
              <CalendarCheck className="h-8 w-8" />
            </div>
            <h3 className="text-2xl font-bold text-foreground">Booking Confirmed!</h3>
            <p className="text-sm text-muted-foreground">{successMessage}</p>

            <div className="bg-card p-4 rounded-xl border border-border text-left space-y-2 text-sm">
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Service:</span>
                <span className="font-medium text-foreground">{selectedService.name}</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Date & Time:</span>
                <span className="font-medium text-foreground">
                  {selectedDate} at {selectedTime}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Attendee:</span>
                <span className="font-medium text-foreground">{customer.fullName} ({customer.email})</span>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={() => {
                setIsConfirmed(false)
                setCustomer({ fullName: "", email: "", phone: "", notes: "" })
              }}
              className="mt-4"
            >
              Book Another Appointment
            </Button>
          </Card>
        ) : (
          /* Booking Form Grid */
          <form onSubmit={handleBooking} className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Step 1: Select Service & Date/Time (Left 7 Cols) */}
            <div className="lg:col-span-7 space-y-6">
              {/* Service Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-semibold">1. Choose Service</Label>
                <div className="grid grid-cols-1 gap-3">
                  {services.map((srv) => (
                    <div
                      key={srv.id}
                      onClick={() => setSelectedServiceId(srv.id)}
                      className={cn(
                        "p-4 rounded-xl border cursor-pointer transition-all flex items-center justify-between",
                        selectedServiceId === srv.id
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-border hover:border-border/80 bg-card"
                      )}
                    >
                      <div className="space-y-1">
                        <div className="font-semibold text-sm sm:text-base text-foreground">
                          {srv.name}
                        </div>
                        {srv.description && (
                          <div className="text-xs text-muted-foreground">{srv.description}</div>
                        )}
                        <div className="flex items-center gap-1.5 text-xs text-primary font-medium pt-1">
                          <Clock className="h-3.5 w-3.5" />
                          <span>{srv.duration}</span>
                        </div>
                      </div>
                      <div className="text-right font-bold text-foreground sm:text-lg pl-3">
                        {srv.price}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Date & Time Selection */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="space-y-2">
                  <Label htmlFor="book-date" className="text-sm font-semibold">
                    2. Select Date <span className="text-destructive">*</span>
                  </Label>
                  <div className="relative">
                    <Input
                      id="book-date"
                      type="date"
                      value={selectedDate}
                      onChange={(e) => setSelectedDate(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-semibold">
                    3. Select Time Slot <span className="text-destructive">*</span>
                  </Label>
                  <div className="grid grid-cols-2 gap-2">
                    {timeSlots.map((slot) => (
                      <button
                        key={slot}
                        type="button"
                        onClick={() => setSelectedTime(slot)}
                        className={cn(
                          "py-2 px-2 rounded-lg text-xs font-medium border text-center transition-colors",
                          selectedTime === slot
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-card border-border hover:bg-muted text-foreground"
                        )}
                      >
                        {slot}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2: Customer Details & Confirmation (Right 5 Cols) */}
            <div className="lg:col-span-5">
              <Card className="border-border shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg font-bold">Your Details</CardTitle>
                  <CardDescription className="text-xs">
                    Please provide your contact information to finalize the booking.
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4">
                  {error && (
                    <div className="p-3 rounded-md bg-destructive/10 text-destructive text-xs">
                      {error}
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="fullname">
                      Full Name <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="fullname"
                      placeholder="Alex Mercer"
                      value={customer.fullName}
                      onChange={(e) =>
                        setCustomer({ ...customer, fullName: e.target.value })
                      }
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="booking-email">
                      Email Address <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="booking-email"
                      type="email"
                      placeholder="alex@example.com"
                      value={customer.email}
                      onChange={(e) =>
                        setCustomer({ ...customer, email: e.target.value })
                      }
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="booking-phone">Phone Number</Label>
                    <Input
                      id="booking-phone"
                      type="tel"
                      placeholder="+1 (555) 019-2834"
                      value={customer.phone}
                      onChange={(e) =>
                        setCustomer({ ...customer, phone: e.target.value })
                      }
                    />
                  </div>

                  {/* Summary Box */}
                  <div className="p-3.5 rounded-lg bg-muted/60 border border-border/80 space-y-1 text-xs text-muted-foreground">
                    <div className="flex justify-between font-medium text-foreground">
                      <span>{selectedService.name}</span>
                      <span>{selectedService.price}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>
                        {selectedDate || "Select date"} at {selectedTime || "Select time"}
                      </span>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full gap-2 font-medium"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Scheduling...
                      </>
                    ) : (
                      <>
                        <CalendarCheck className="h-4 w-4" />
                        {submitButtonText}
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </form>
        )}
      </div>
    </section>
  )
}
