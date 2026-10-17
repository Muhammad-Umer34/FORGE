// Multi-platform social proof bar with automated URL normalization from handles and dedicated platform icons

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Globe, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SocialHandlesMap {
  instagram?: string
  facebook?: string
  tiktok?: string
  youtube?: string
  x?: string
  linkedin?: string
  whatsapp?: string
}

export interface SocialLinksBarProps {
  badgeText?: string
  title?: string
  subtitle?: string
  handles?: SocialHandlesMap
  layout?: "pills" | "grid"
  className?: string
}

interface PlatformConfig {
  name: string
  buildUrl: (val: string) => string
  icon: (className?: string) => React.ReactNode
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
    </svg>
  )
}

function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
    </svg>
  )
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
      <rect width="4" height="12" x="2" y="9" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  )
}

function YouTubeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17" />
      <path d="m10 15 5-3-5-3z" />
    </svg>
  )
}

function TikTokIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.97v7.54c.01 2.21-.76 4.43-2.22 6.09-1.74 1.99-4.36 3.14-7.05 3.09-2.6-.04-5.11-1.14-6.84-3.04-1.77-1.92-2.68-4.57-2.49-7.18.2-2.58 1.53-4.99 3.59-6.49 1.95-1.43 4.45-2.03 6.84-1.64v4.1c-1.32-.38-2.77-.2-3.92.51-1.07.66-1.76 1.87-1.78 3.13-.02 1.25.64 2.47 1.69 3.15 1.09.7 2.49.81 3.69.31 1.01-.42 1.74-1.42 1.78-2.51V.02h.87z" />
    </svg>
  )
}

const PLATFORMS: Record<string, PlatformConfig> = {
  instagram: {
    name: "Instagram",
    buildUrl: (val) => (val.startsWith("http") ? val : `https://instagram.com/${val.replace(/^@/, "")}`),
    icon: (cls) => <InstagramIcon className={cls} />,
  },
  facebook: {
    name: "Facebook",
    buildUrl: (val) => (val.startsWith("http") ? val : `https://facebook.com/${val.replace(/^@/, "")}`),
    icon: (cls) => <FacebookIcon className={cls} />,
  },
  tiktok: {
    name: "TikTok",
    buildUrl: (val) => (val.startsWith("http") ? val : `https://tiktok.com/@${val.replace(/^@/, "")}`),
    icon: (cls) => <TikTokIcon className={cls} />,
  },
  youtube: {
    name: "YouTube",
    buildUrl: (val) => (val.startsWith("http") ? val : `https://youtube.com/@${val.replace(/^@/, "")}`),
    icon: (cls) => <YouTubeIcon className={cls} />,
  },
  x: {
    name: "X (Twitter)",
    buildUrl: (val) => (val.startsWith("http") ? val : `https://x.com/${val.replace(/^@/, "")}`),
    icon: (cls) => <XIcon className={cls} />,
  },
  linkedin: {
    name: "LinkedIn",
    buildUrl: (val) =>
      val.startsWith("http") ? val : `https://linkedin.com/company/${val.replace(/^@/, "")}`,
    icon: (cls) => <LinkedInIcon className={cls} />,
  },
  whatsapp: {
    name: "WhatsApp",
    buildUrl: (val) => (val.startsWith("http") ? val : `https://wa.me/${val.replace(/[^0-9]/g, "")}`),
    icon: (cls) => <MessageCircle className={cls} />,
  },
}

export function SocialLinksBar({
  badgeText = "Connect With Us",
  title = "Follow Our Journey Online",
  subtitle = "Stay updated on news, announcements, and behind-the-scenes content across our official channels.",
  handles = {
    instagram: "yourbrand",
    facebook: "yourbrand",
    x: "yourbrand",
    linkedin: "yourbrand",
    youtube: "yourbrand",
  },
  layout = "pills",
  className,
}: SocialLinksBarProps) {
  const activeItems = Object.entries(handles || {})
    .filter(([platform, val]) => Boolean(val && val.trim().length > 0 && PLATFORMS[platform]))
    .map(([platform, val]) => {
      const cfg = PLATFORMS[platform]
      return {
        key: platform,
        name: cfg.name,
        url: cfg.buildUrl(val!.trim()),
        icon: cfg.icon,
      }
    })

  if (activeItems.length === 0) {
    return null
  }

  return (
    <section id="social-links" className={cn("w-full py-12 sm:py-16 bg-background border-b border-border/40", className)}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Header */}
        <div className="space-y-3 mb-8">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-sm text-muted-foreground max-w-xl mx-auto">{subtitle}</p>}
        </div>

        {/* Links Display */}
        {layout === "pills" ? (
          <div className="flex flex-wrap items-center justify-center gap-3">
            {activeItems.map((item) => (
              <a
                key={item.key}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-card hover:bg-accent border border-border text-foreground hover:text-primary transition-all duration-150 shadow-sm text-xs font-semibold"
                aria-label={`Visit our ${item.name} page`}
              >
                <div className="h-4 w-4 shrink-0 transition-transform group-hover:scale-110">
                  {item.icon("h-4 w-4")}
                </div>
                <span>{item.name}</span>
              </a>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {activeItems.map((item) => (
              <a
                key={item.key}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group p-5 rounded-2xl bg-card hover:bg-accent border border-border text-foreground hover:border-primary/40 transition-all duration-150 shadow-sm flex flex-col items-center justify-center gap-3 text-center"
                aria-label={`Visit our ${item.name} page`}
              >
                <div className="h-8 w-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center transition-transform group-hover:scale-110">
                  {item.icon("h-4 w-4")}
                </div>
                <span className="text-xs font-semibold">{item.name}</span>
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
