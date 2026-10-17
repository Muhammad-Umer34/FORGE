// Accessible lead capture conversion modal with exit-intent trigger, delay timer, email submission, and session-remembered suppression

"use client"

import React, { useState, useEffect, useRef } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { X, Mail, Sparkles, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LeadCapturePopupProps {
  badgeText?: string
  title?: string
  description?: string
  offerBadge?: string
  placeholder?: string
  buttonText?: string
  disclaimer?: string
  delaySeconds?: number // opens automatically after seconds (0 disables timer)
  triggerOnExitIntent?: boolean
  onSubmit?: (email: string) => Promise<void> | void
  storageKey?: string
  className?: string
}

export function LeadCapturePopup({
  badgeText = "Special Invitation",
  title = "Unlock 15% Off Your First Order",
  description = "Join our community newsletter and receive an instant promotional discount code for your first booking or order.",
  offerBadge = "15% OFF",
  placeholder = "Enter your email address",
  buttonText = "Claim My Offer",
  disclaimer = "No spam, unsubscribe anytime. Offer valid for new clients.",
  delaySeconds = 6,
  triggerOnExitIntent = true,
  onSubmit,
  storageKey = "forge_lead_popup_dismissed",
  className,
}: LeadCapturePopupProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const modalRef = useRef<HTMLDivElement>(null)

  // Session check and timer trigger
  useEffect(() => {
    if (typeof window === "undefined") return

    let isDismissed = false
    try {
      isDismissed = sessionStorage.getItem(storageKey) === "true"
    } catch {
      // Ignore
    }

    if (isDismissed) return

    // Timer trigger
    let timer: NodeJS.Timeout | null = null
    if (delaySeconds > 0) {
      timer = setTimeout(() => {
        setIsOpen(true)
      }, delaySeconds * 1000)
    }

    // Exit intent trigger (detect cursor moving to top of window)
    const handleMouseLeave = (e: MouseEvent) => {
      if (triggerOnExitIntent && e.clientY <= 0) {
        setIsOpen(true)
      }
    }

    document.addEventListener("mouseleave", handleMouseLeave)

    return () => {
      if (timer) clearTimeout(timer)
      document.removeEventListener("mouseleave", handleMouseLeave)
    }
  }, [delaySeconds, triggerOnExitIntent, storageKey])

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen])

  const handleClose = () => {
    setIsOpen(false)
    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(storageKey, "true")
      } catch {
        // Ignore
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const trimmed = email.trim()
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!trimmed || !emailRegex.test(trimmed)) {
      setError("Please provide a valid email address.")
      return
    }

    try {
      setIsSubmitting(true)
      if (onSubmit) {
        await onSubmit(trimmed)
      } else {
        await new Promise((resolve) => setTimeout(resolve, 700))
      }
      setIsSubmitted(true)
      setTimeout(() => {
        handleClose()
      }, 2500)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to claim offer. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) {
    return null
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="lead-popup-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div
        ref={modalRef}
        className={cn(
          "relative w-full max-w-lg rounded-2xl bg-card border border-border shadow-2xl p-6 sm:p-8 animate-in zoom-in-95 duration-200",
          className
        )}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={handleClose}
          aria-label="Close dialog"
          className="absolute top-4 right-4 p-1.5 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <X className="h-5 w-5" />
        </button>

        {isSubmitted ? (
          <div className="text-center py-6 space-y-3">
            <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
              <CheckCircle2 className="h-7 w-7" />
            </div>
            <h3 className="text-2xl font-bold text-foreground">You&apos;re On the List!</h3>
            <p className="text-sm text-muted-foreground">
              Check your inbox shortly for your exclusive discount voucher code.
            </p>
          </div>
        ) : (
          <div className="space-y-6 text-center">
            {/* Offer Badge & Header */}
            <div className="space-y-3">
              <div className="flex items-center justify-center gap-2">
                {offerBadge && (
                  <Badge className="bg-primary text-primary-foreground text-xs font-black px-2.5 py-0.5 shadow-xs">
                    {offerBadge}
                  </Badge>
                )}
                {badgeText && (
                  <Badge variant="outline" className="text-primary border-primary/30 text-xs">
                    {badgeText}
                  </Badge>
                )}
              </div>

              <h2 id="lead-popup-title" className="text-2xl sm:text-3xl font-black tracking-tight text-foreground">
                {title}
              </h2>

              {description && (
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-sm mx-auto">
                  {description}
                </p>
              )}
            </div>

            {/* Email Form */}
            <form onSubmit={handleSubmit} className="space-y-3 max-w-sm mx-auto">
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={placeholder}
                  className="pl-10 text-sm h-11"
                  required
                />
              </div>

              {error && (
                <div className="p-2 rounded-lg bg-destructive/10 text-destructive text-xs flex items-center justify-center gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button type="submit" disabled={isSubmitting} className="w-full h-11 font-bold text-sm gap-2">
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Claiming...
                  </>
                ) : (
                  buttonText
                )}
              </Button>

              {disclaimer && (
                <p className="text-[11px] text-muted-foreground pt-1">{disclaimer}</p>
              )}
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
