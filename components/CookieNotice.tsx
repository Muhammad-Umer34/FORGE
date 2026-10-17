// Bottom floating privacy and cookie consent notice with localStorage persistence and graceful fallback

"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { ShieldCheck, X } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CookieNoticeProps {
  message?: string
  acceptButtonText?: string
  declineButtonText?: string
  privacyPolicyHref?: string
  privacyPolicyLabel?: string
  storageKey?: string
  onAccept?: () => void
  onDecline?: () => void
  className?: string
}

export function CookieNotice({
  message = "We use essential cookies to maintain system functionality and improve your browsing experience. By continuing to use our website, you agree to our privacy policy.",
  acceptButtonText = "Accept All",
  declineButtonText = "Essential Only",
  privacyPolicyHref = "#privacy",
  privacyPolicyLabel = "Privacy Policy",
  storageKey = "forge_cookie_notice_accepted",
  onAccept,
  onDecline,
  className,
}: CookieNoticeProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(storageKey)
        if (!stored) {
          setIsVisible(true)
        }
      } catch {
        // Fallback if localStorage is disabled in browser sandbox
        setIsVisible(true)
      }
    }
  }, [storageKey])

  const handleAccept = () => {
    setIsVisible(false)
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(storageKey, "accepted")
      } catch {
        // Ignore
      }
    }
    onAccept?.()
  }

  const handleDecline = () => {
    setIsVisible(false)
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(storageKey, "declined")
      } catch {
        // Ignore
      }
    }
    onDecline?.()
  }

  if (!isVisible) {
    return null
  }

  return (
    <aside
      role="region"
      aria-label="Cookie Consent Notice"
      className={cn(
        "fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:max-w-md z-50",
        "p-5 rounded-2xl bg-card/95 backdrop-blur-md border border-border shadow-2xl",
        "animate-in slide-in-from-bottom-4 duration-300",
        className
      )}
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Privacy & Cookies</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {message}{" "}
              {privacyPolicyHref && (
                <a
                  href={privacyPolicyHref}
                  className="font-semibold text-primary underline underline-offset-2 hover:opacity-80"
                >
                  {privacyPolicyLabel}
                </a>
              )}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-1 border-t border-border/40">
          {declineButtonText && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDecline}
              className="text-xs h-8 px-3"
            >
              {declineButtonText}
            </Button>
          )}
          <Button
            size="sm"
            onClick={handleAccept}
            className="text-xs h-8 px-4 font-semibold shadow-xs"
          >
            {acceptButtonText}
          </Button>
        </div>
      </div>
    </aside>
  )
}
