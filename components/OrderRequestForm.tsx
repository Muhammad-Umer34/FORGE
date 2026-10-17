// Customer order request form with item quantity selection, delivery/pickup date, notes, and contact details (no payment required)

"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ShoppingBag, Calendar, User, Phone, Mail, CheckCircle2, Plus, Minus, AlertCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface OrderItem {
  id: string
  name: string
  price?: string
  description?: string
  imageUrl?: string
}

export interface SelectedItemQuantity {
  item: OrderItem
  quantity: number
}

export interface OrderRequestData {
  items: { itemId: string; name: string; quantity: number; price?: string }[]
  requiredDate: string
  notes?: string
  customerName: string
  phone: string
  email?: string
}

export interface OrderRequestFormProps {
  badgeText?: string
  title?: string
  subtitle?: string
  items?: OrderItem[]
  dateLabel?: string
  submitLabel?: string
  onSubmit?: (data: OrderRequestData) => Promise<void> | void
  successTitle?: string
  successMessage?: string
  className?: string
}

export function OrderRequestForm({
  badgeText = "Order Request",
  title = "Place an Order Request",
  subtitle = "Select the items and quantities you wish to order. We will review your request and get back to you shortly.",
  items = [
    {
      id: "item-1",
      name: "Item Name 1",
      price: "$20.00",
      description: "Standard description for the first catalog item.",
    },
    {
      id: "item-2",
      name: "Item Name 2",
      price: "$35.00",
      description: "Standard description for the second catalog item.",
    },
    {
      id: "item-3",
      name: "Item Name 3",
      price: "$15.00",
      description: "Standard description for the third catalog item.",
    },
  ],
  dateLabel = "Required Date",
  submitLabel = "Submit Order Request",
  onSubmit,
  successTitle = "Request Received!",
  successMessage = "Thank you! Your order request has been received. Our team will contact you to confirm details.",
  className,
}: OrderRequestFormProps) {
  const [quantities, setQuantities] = useState<Record<string, number>>({})
  const [requiredDate, setRequiredDate] = useState("")
  const [notes, setNotes] = useState("")
  const [customer, setCustomer] = useState({
    name: "",
    phone: "",
    email: "",
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleQuantityChange = (itemId: string, delta: number) => {
    setQuantities((prev) => {
      const current = prev[itemId] || 0
      const next = Math.max(0, current + delta)
      return { ...prev, [itemId]: next }
    })
  }

  const selectedItemsList = (items || []).filter((item) => (quantities[item.id] || 0) > 0)
  const totalQuantity = Object.values(quantities).reduce((acc, q) => acc + q, 0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (totalQuantity === 0) {
      setError("Please select at least one item with a quantity greater than zero.")
      return
    }

    if (!customer.name.trim()) {
      setError("Please enter your name.")
      return
    }

    const cleanPhone = customer.phone.replace(/[^0-9+]/g, "")
    if (!cleanPhone || cleanPhone.length < 7) {
      setError("Please provide a valid contact phone number.")
      return
    }

    if (!requiredDate) {
      setError("Please select your desired date.")
      return
    }

    const payload: OrderRequestData = {
      items: selectedItemsList.map((item) => ({
        itemId: item.id,
        name: item.name,
        quantity: quantities[item.id] || 0,
        price: item.price,
      })),
      requiredDate,
      notes: notes.trim() || undefined,
      customerName: customer.name.trim(),
      phone: customer.phone.trim(),
      email: customer.email.trim() || undefined,
    }

    try {
      setIsSubmitting(true)
      if (onSubmit) {
        await onSubmit(payload)
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800))
      }
      setIsSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit request. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isSubmitted) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40", className)}>
        <div className="max-w-xl mx-auto px-4 text-center">
          <Card className="p-8 border-primary/20 bg-card shadow-sm">
            <div className="h-14 w-14 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <h3 className="text-2xl font-bold text-foreground mb-2">{successTitle}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">{successMessage}</p>
            <div className="p-4 rounded-lg bg-muted/50 text-left text-xs space-y-2 mb-6">
              <div className="font-semibold text-foreground">Order Request Summary:</div>
              {selectedItemsList.map((item) => (
                <div key={item.id} className="flex justify-between text-muted-foreground">
                  <span>{item.name} × {quantities[item.id]}</span>
                  {item.price && <span>{item.price}</span>}
                </div>
              ))}
              <div className="pt-2 border-t border-border flex justify-between font-medium text-foreground">
                <span>Date:</span>
                <span>{requiredDate}</span>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                setIsSubmitted(false)
                setQuantities({})
                setRequiredDate("")
                setNotes("")
                setCustomer({ name: "", phone: "", email: "" })
              }}
            >
              Submit Another Request
            </Button>
          </Card>
        </div>
      </section>
    )
  }

  if (!items || items.length === 0) {
    return (
      <section className={cn("w-full py-12 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <ShoppingBag className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No items are currently available for ordering.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="order-request" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center space-y-3 mb-10">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground max-w-2xl mx-auto">{subtitle}</p>}
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Item Selection Cards */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-3 border-b border-border/60">
              <CardTitle className="text-lg flex items-center gap-2">
                <ShoppingBag className="h-5 w-5 text-primary" />
                Select Items & Quantities
              </CardTitle>
              <CardDescription>Adjust the quantity for each item you want to include in this request.</CardDescription>
            </CardHeader>
            <CardContent className="pt-4 divide-y divide-border/60">
              {items.map((item) => {
                const qty = quantities[item.id] || 0
                return (
                  <div key={item.id} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                      {item.imageUrl && (
                        <img
                          src={item.imageUrl}
                          alt={item.name}
                          className="h-14 w-14 rounded-lg object-cover bg-muted shrink-0"
                        />
                      )}
                      <div>
                        <div className="font-semibold text-foreground text-sm sm:text-base">{item.name}</div>
                        {item.description && <div className="text-xs text-muted-foreground mt-0.5">{item.description}</div>}
                        {item.price && <div className="text-xs font-semibold text-primary mt-1">{item.price}</div>}
                      </div>
                    </div>
                    {/* Stepper Buttons */}
                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 rounded-md"
                        onClick={() => handleQuantityChange(item.id, -1)}
                        disabled={qty === 0}
                        aria-label={`Decrease quantity for ${item.name}`}
                      >
                        <Minus className="h-3.5 w-3.5" />
                      </Button>
                      <span className="w-8 text-center font-semibold text-sm tabular-nums" aria-live="polite">
                        {qty}
                      </span>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 rounded-md"
                        onClick={() => handleQuantityChange(item.id, 1)}
                        aria-label={`Increase quantity for ${item.name}`}
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                )
              })}
            </CardContent>
          </Card>

          {/* Details & Contact Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Required Date & Notes */}
            <Card className="border-border bg-card">
              <CardHeader className="pb-3 border-b border-border/60">
                <CardTitle className="text-base flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-primary" />
                  Schedule & Requirements
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="order-date" className="text-xs font-medium">
                    {dateLabel} <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="order-date"
                    type="date"
                    value={requiredDate}
                    onChange={(e) => setRequiredDate(e.target.value)}
                    required
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="order-notes" className="text-xs font-medium">
                    Special Notes or Custom Requests
                  </Label>
                  <Textarea
                    id="order-notes"
                    placeholder="E.g., dietary restrictions, packaging preferences, preferred pickup time..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    className="text-sm resize-none"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Customer Contact */}
            <Card className="border-border bg-card">
              <CardHeader className="pb-3 border-b border-border/60">
                <CardTitle className="text-base flex items-center gap-2">
                  <User className="h-4 w-4 text-primary" />
                  Your Contact Information
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="customer-name" className="text-xs font-medium">
                    Full Name <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="customer-name"
                    placeholder="Your Name"
                    value={customer.name}
                    onChange={(e) => setCustomer({ ...customer, name: e.target.value })}
                    required
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="customer-phone" className="text-xs font-medium">
                    Phone Number <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="customer-phone"
                    type="tel"
                    placeholder="+1 (555) 000-0000"
                    value={customer.phone}
                    onChange={(e) => setCustomer({ ...customer, phone: e.target.value })}
                    required
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="customer-email" className="text-xs font-medium">
                    Email Address (Optional)
                  </Label>
                  <Input
                    id="customer-email"
                    type="email"
                    placeholder="name@example.com"
                    value={customer.email}
                    onChange={(e) => setCustomer({ ...customer, email: e.target.value })}
                    className="text-sm"
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Validation Error Message */}
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Action Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-muted/40 border border-border">
            <div className="text-xs text-muted-foreground text-center sm:text-left">
              Total items selected: <strong className="text-foreground">{totalQuantity}</strong>. No payment collected today.
            </div>
            <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto px-6 gap-2">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting Request...
                </>
              ) : (
                submitLabel
              )}
            </Button>
          </div>
        </form>
      </div>
    </section>
  )
}
