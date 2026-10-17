// Floating fixed-corner WhatsApp call-to-action button with digit-sanitized URL generation and optional prefilled chat message

"use client"

import React from "react"
import { MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface WhatsAppButtonProps {
  phoneNumber?: string
  prefilledMessage?: string
  label?: string
  position?: "bottom-right" | "bottom-left"
  showLabelOnMobile?: boolean
  className?: string
}

export function WhatsAppButton({
  phoneNumber = "15551234567",
  prefilledMessage = "Hello! I would like to inquire about your services.",
  label = "Chat with us",
  position = "bottom-right",
  showLabelOnMobile = false,
  className,
}: WhatsAppButtonProps) {
  // Strip all non-digit characters for standard wa.me API specification
  const cleanNumber = (phoneNumber || "").replace(/[^0-9]/g, "")

  // Do not render anything if no valid phone digits exist
  if (!cleanNumber) {
    return null
  }

  const encodedMessage = prefilledMessage ? `?text=${encodeURIComponent(prefilledMessage)}` : ""
  const whatsappUrl = `https://wa.me/${cleanNumber}${encodedMessage}`

  const positionClasses =
    position === "bottom-left"
      ? "bottom-6 left-6"
      : "bottom-6 right-6"

  return (
    <aside
      aria-label="Direct WhatsApp Contact"
      className={cn("fixed z-50", positionClasses, className)}
    >
      <a
        href={whatsappUrl}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`${label} on WhatsApp`}
        className={cn(
          "group flex items-center gap-2.5 px-4 py-3 sm:py-3.5 rounded-full shadow-lg transition-all duration-200",
          "bg-emerald-600 hover:bg-emerald-500 text-white hover:scale-105 active:scale-95",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2",
          "border border-emerald-500/30"
        )}
      >
        <MessageCircle className="h-5 w-5 shrink-0 fill-current" />
        <span
          className={cn(
            "text-sm font-semibold tracking-wide whitespace-nowrap",
            showLabelOnMobile ? "inline" : "hidden sm:inline"
          )}
        >
          {label}
        </span>
      </a>
    </aside>
  )
}
