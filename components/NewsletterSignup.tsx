// Newsletter email subscription section with privacy consent checkbox, client validation, loading state, and success feedback

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card } from "@/components/ui/card"
import { Mail, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface NewsletterSignupProps {
  badgeText?: string
  title?: string
  subtitle?: string
  placeholder?: string
  buttonText?: string
  consentText?: string
  onSubmit?: (email: string) => Promise<void> | void
  successTitle?: string
  successMessage?: string
  className?: string
}

export function NewsletterSignup({
  badgeText = "Newsletter",
  title = "Stay in the Loop",
  subtitle = "Subscribe to receive our latest updates, exclusive promotions, and helpful insights straight to your inbox.",
  placeholder = "Enter your email address",
  buttonText = "Subscribe",
  consentText = "I agree to receive email communications and accept the privacy policy. You can unsubscribe at any time.",
  onSubmit,
  successTitle = "You're Subscribed!",
  successMessage = "Thank you for joining our community! Look out for our welcome email shortly.",
  className,
}: NewsletterSignupProps) {
  const [email, setEmail] = useState("")
  const [consent, setConsent] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const trimmed = email.trim()
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!trimmed || !emailRegex.test(trimmed)) {
      setError("Please enter a valid email address.")
      return
    }

    if (!consent) {
      setError("Please agree to the privacy and communication terms to proceed.")
      return
    }

    try {
      setIsSubmitting(true)
      if (onSubmit) {
        await onSubmit(trimmed)
      } else {
        await new Promise((resolve) => setTimeout(resolve, 700))
      }
      setIsSubscribed(true)
      setEmail("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to subscribe. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section id="newsletter" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <Card className="relative overflow-hidden p-8 sm:p-12 border-border bg-card shadow-sm text-center">
          {/* Subtle Accent Glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-primary/10 blur-3xl -z-10 rounded-full" />

          {isSubscribed ? (
            <div className="max-w-md mx-auto space-y-4 py-4 animate-in fade-in zoom-in-95 duration-200">
              <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h3 className="text-2xl font-bold text-foreground">{successTitle}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{successMessage}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsSubscribed(false)
                  setConsent(false)
                }}
              >
                Subscribe Another Email
              </Button>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-6">
              {/* Header */}
              <div className="space-y-3">
                {badgeText && (
                  <Badge variant="outline" className="text-primary border-primary/30">
                    {badgeText}
                  </Badge>
                )}
                <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
                {subtitle && <p className="text-sm sm:text-base text-muted-foreground">{subtitle}</p>}
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4 pt-2">
                <div className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
                  <div className="relative flex-1">
                    <Label htmlFor="newsletter-email" className="sr-only">
                      Email address
                    </Label>
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="newsletter-email"
                      type="email"
                      placeholder={placeholder}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 text-sm h-11"
                      required
                    />
                  </div>
                  <Button type="submit" disabled={isSubmitting} className="h-11 px-6 font-semibold shrink-0 gap-2">
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Joining...
                      </>
                    ) : (
                      buttonText
                    )}
                  </Button>
                </div>

                {/* Consent Checkbox */}
                <div className="flex items-start justify-center gap-2 max-w-md mx-auto text-left">
                  <input
                    type="checkbox"
                    id="newsletter-consent"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer shrink-0"
                  />
                  <Label htmlFor="newsletter-consent" className="text-xs text-muted-foreground cursor-pointer leading-tight">
                    {consentText}
                  </Label>
                </div>

                {/* Error Banner */}
                {error && (
                  <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs max-w-md mx-auto flex items-center justify-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}
              </form>
            </div>
          )}
        </Card>
      </div>
    </section>
  )
}
