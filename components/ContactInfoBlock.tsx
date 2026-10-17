// Direct business contact information block displaying phone, email, physical address, and social links with automatic omission of missing rows

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Phone, Mail, MapPin, Globe, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SocialLinks {
  instagram?: string
  facebook?: string
  twitter?: string
  linkedin?: string
  whatsapp?: string
  youtube?: string
  [key: string]: string | undefined
}

export interface ContactInfoBlockProps {
  badgeText?: string
  title?: string
  subtitle?: string
  phone?: string
  email?: string
  address?: string
  socialHandles?: SocialLinks
  className?: string
}

export function ContactInfoBlock({
  badgeText = "Contact Details",
  title = "How to Reach Us",
  subtitle = "Have questions or want to collaborate? Connect with us through any of the channels below.",
  phone = "+1 (555) 000-0000",
  email = "hello@example.com",
  address = "123 Business Way, Suite 100, City, Country",
  socialHandles = {
    instagram: "https://instagram.com",
    facebook: "https://facebook.com",
    linkedin: "https://linkedin.com",
  },
  className,
}: ContactInfoBlockProps) {
  const hasPhone = Boolean(phone && phone.trim().length > 0)
  const hasEmail = Boolean(email && email.trim().length > 0)
  const hasAddress = Boolean(address && address.trim().length > 0)

  const activeSocials = Object.entries(socialHandles || {}).filter(
    ([_, url]) => url && url.trim().length > 0
  )
  const hasSocials = activeSocials.length > 0

  const hasAnyContact = hasPhone || hasEmail || hasAddress || hasSocials

  if (!hasAnyContact) {
    return null
  }

  return (
    <section id="contact-info" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center space-y-3 mb-12">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground max-w-xl mx-auto">{subtitle}</p>}
        </div>

        {/* Contact Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Phone */}
          {hasPhone && (
            <Card className="border-border bg-card p-6 flex flex-col justify-between hover:border-primary/40 transition-colors">
              <div className="space-y-3">
                <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <Phone className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground text-sm">Call Us Directly</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Mon–Fri during business hours</p>
                </div>
              </div>
              <div className="pt-4 mt-4 border-t border-border/60">
                <a
                  href={`tel:${phone}`}
                  className="text-sm font-semibold text-primary hover:underline break-all"
                >
                  {phone}
                </a>
              </div>
            </Card>
          )}

          {/* Email */}
          {hasEmail && (
            <Card className="border-border bg-card p-6 flex flex-col justify-between hover:border-primary/40 transition-colors">
              <div className="space-y-3">
                <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <Mail className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground text-sm">Email Inquiries</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">We typically reply within 24 hours</p>
                </div>
              </div>
              <div className="pt-4 mt-4 border-t border-border/60">
                <a
                  href={`mailto:${email}`}
                  className="text-sm font-semibold text-primary hover:underline break-all"
                >
                  {email}
                </a>
              </div>
            </Card>
          )}

          {/* Address */}
          {hasAddress && (
            <Card className="border-border bg-card p-6 flex flex-col justify-between hover:border-primary/40 transition-colors sm:col-span-2 lg:col-span-1">
              <div className="space-y-3">
                <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground text-sm">Main Office</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Physical location & mailing</p>
                </div>
              </div>
              <div className="pt-4 mt-4 border-t border-border/60">
                <p className="text-sm font-medium text-foreground leading-snug">
                  {address}
                </p>
              </div>
            </Card>
          )}
        </div>

        {/* Social Handles Bar */}
        {hasSocials && (
          <div className="mt-8 p-6 rounded-2xl bg-muted/30 border border-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-center sm:text-left">
              <h4 className="text-sm font-semibold text-foreground">Follow Us Online</h4>
              <p className="text-xs text-muted-foreground">Stay connected through our active social channels</p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {activeSocials.map(([platform, url]) => (
                <a
                  key={platform}
                  href={url?.startsWith("http") ? url : `https://${url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-background hover:bg-accent text-foreground border border-border transition-colors capitalize flex items-center gap-1.5"
                >
                  {platform.toLowerCase().includes("whatsapp") ? (
                    <MessageCircle className="h-3.5 w-3.5 text-emerald-500" />
                  ) : (
                    <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  {platform}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
