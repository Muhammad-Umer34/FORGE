// Structured legal document template for Privacy Policy and Terms of Service with section navigation anchors

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { ShieldCheck, Calendar, Mail, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LegalSection {
  id: string
  title: string
  content: string
}

export interface LegalPageProps {
  badgeText?: string
  title?: string
  lastUpdated?: string
  companyName?: string
  contactEmail?: string
  sections?: LegalSection[]
  className?: string
}

export function LegalPage({
  badgeText = "Legal Compliance",
  title = "Privacy Policy & Terms of Service",
  lastUpdated = "October 10, 2026",
  companyName = "Our Company",
  contactEmail = "privacy@example.com",
  sections = [
    {
      id: "introduction",
      title: "1. Introduction & Overview",
      content: "This Privacy Policy and Terms of Service outlines how we collect, handle, and safeguard customer data when you interact with our website, order items, or book consultations. We respect your personal privacy and operate strictly in accordance with applicable data protection laws.",
    },
    {
      id: "data-collection",
      title: "2. Information We Collect",
      content: "We only collect data necessary to provide our services. This includes contact details (such as your full name, email address, and telephone number) submitted through order forms, inquiry messages, or newsletter subscriptions. We do not store sensitive payment card details directly on our servers.",
    },
    {
      id: "use-of-info",
      title: "3. How Information Is Used",
      content: "Your information is used strictly to fulfill order requests, schedule appointment consultations, respond to customer inquiries, and provide essential service updates. We never sell or license your personal contact details to third-party advertising brokers.",
    },
    {
      id: "cookies",
      title: "4. Cookies & Local Storage",
      content: "We employ strictly necessary cookies and local storage tokens to remember your preferences (such as dismissed announcement banners and cookie consent choices). You can adjust your browser settings to decline cookies at any time.",
    },
    {
      id: "contact",
      title: "5. Contact & Questions",
      content: "If you have any questions regarding your data, privacy rights, or terms of use, please reach out to our privacy compliance officer directly.",
    },
  ],
  className,
}: LegalPageProps) {
  return (
    <article className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        {/* Header Block */}
        <header className="space-y-4 text-center max-w-3xl mx-auto">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-foreground">
            {title}
          </h1>

          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground pt-1">
            <Calendar className="h-3.5 w-3.5" />
            <span>Last Updated: {lastUpdated}</span>
            <span>•</span>
            <span>{companyName}</span>
          </div>
        </header>

        {/* Layout Grid: Sidebar Anchor Navigation + Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          {/* Sidebar Table of Contents (4 cols) */}
          {sections && sections.length > 0 && (
            <div className="hidden lg:block lg:col-span-4 sticky top-24">
              <Card className="p-5 border-border bg-card shadow-xs space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground pb-2 border-b border-border">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                  <span>Document Sections</span>
                </div>
                <nav className="space-y-1.5 text-xs">
                  {sections.map((sec) => (
                    <a
                      key={sec.id}
                      href={`#${sec.id}`}
                      className="block p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors line-clamp-1"
                    >
                      {sec.title}
                    </a>
                  ))}
                </nav>
              </Card>
            </div>
          )}

          {/* Legal Clauses Body (8 cols) */}
          <div className="lg:col-span-8 space-y-10">
            {sections?.map((sec) => (
              <section key={sec.id} id={sec.id} className="scroll-mt-24 space-y-3">
                <h2 className="text-xl font-bold text-foreground tracking-tight border-b border-border/60 pb-2">
                  {sec.title}
                </h2>
                <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                  {sec.content}
                </div>
              </section>
            ))}

            {/* Inquiries Note Card */}
            {contactEmail && (
              <div className="p-6 rounded-2xl bg-muted/30 border border-border flex items-start gap-4">
                <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <Mail className="h-5 w-5" />
                </div>
                <div className="space-y-1 text-xs sm:text-sm">
                  <h3 className="font-bold text-foreground">Questions or Concerns?</h3>
                  <p className="text-muted-foreground">
                    For inquiries regarding our terms, please email us directly at{" "}
                    <a href={`mailto:${contactEmail}`} className="font-semibold text-primary hover:underline">
                      {contactEmail}
                    </a>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  )
}
