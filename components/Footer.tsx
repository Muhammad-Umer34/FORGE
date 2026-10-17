// Multi-column website footer with brand summary, categorized navigation links, newsletter signup, and copyright notice

"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Mail, ArrowRight, CheckCircle2, Globe } from "lucide-react"
import { cn } from "@/lib/utils"

export interface FooterColumn {
  title: string
  links: { label: string; href: string }[]
}

export interface FooterProps {
  brandName?: string
  description?: string
  columns?: FooterColumn[]
  newsletterTitle?: string
  newsletterSubtitle?: string
  onNewsletterSubmit?: (email: string) => Promise<void> | void
  copyright?: string
  className?: string
}

export function Footer({
  brandName = "FORGE",
  description = "The next-generation AI web engine that turns natural language ideas into production-ready full stack web applications with live WebContainers preview.",
  columns = [
    {
      title: "Product",
      links: [
        { label: "AI Generator", href: "#" },
        { label: "Section Library", href: "#library" },
        { label: "WebContainers", href: "#" },
        { label: "Live Preview", href: "#" },
      ],
    },
    {
      title: "Resources",
      links: [
        { label: "Documentation", href: "#" },
        { label: "Next.js Integration", href: "#" },
        { label: "Tailwind Styling", href: "#" },
        { label: "API Reference", href: "#" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "About Us", href: "#about" },
        { label: "Pricing", href: "#pricing" },
        { label: "Contact", href: "#contact" },
        { label: "Careers", href: "#" },
      ],
    },
  ],
  newsletterTitle = "Stay Updated",
  newsletterSubtitle = "Get the latest component additions, prompt recipes, and engine upgrades directly to your inbox.",
  onNewsletterSubmit,
  copyright = `© ${new Date().getFullYear()} FORGE Technologies Inc. All rights reserved.`,
  className,
}: FooterProps) {
  const [email, setEmail] = useState("")
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setIsSubmitting(true)
    try {
      if (onNewsletterSubmit) {
        await onNewsletterSubmit(email)
      } else {
        await new Promise((resolve) => setTimeout(resolve, 600))
      }
      setIsSubscribed(true)
      setEmail("")
    } catch {
      // Ignore
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <footer
      className={cn(
        "w-full bg-zinc-950 text-zinc-300 border-t border-zinc-800/80 pt-16 pb-12",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-10 lg:gap-8 pb-12 border-b border-zinc-800">
          {/* Brand Col (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="flex items-center gap-2 font-bold text-xl text-white">
              <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-black text-sm">
                {brandName.charAt(0)}
              </div>
              <span>{brandName}</span>
            </div>

            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed max-w-sm">
              {description}
            </p>

            {/* Social SVG Icons */}
            <div className="flex items-center gap-3 pt-2">
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="h-8 w-8 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center transition-colors"
                aria-label="GitHub"
              >
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
              </a>
              <a
                href="https://twitter.com"
                target="_blank"
                rel="noreferrer"
                className="h-8 w-8 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center transition-colors"
                aria-label="X / Twitter"
              >
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              <a
                href="https://linkedin.com"
                target="_blank"
                rel="noreferrer"
                className="h-8 w-8 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center transition-colors"
                aria-label="LinkedIn"
              >
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                  <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Navigation Columns (5 cols) */}
          <div className="lg:col-span-5 grid grid-cols-2 sm:grid-cols-3 gap-8">
            {columns.map((col, idx) => (
              <div key={idx} className="space-y-3">
                <h4 className="font-semibold text-xs text-white uppercase tracking-wider">
                  {col.title}
                </h4>
                <ul className="space-y-2 text-xs sm:text-sm">
                  {col.links.map((link, lIdx) => (
                    <li key={lIdx}>
                      <a
                        href={link.href}
                        className="text-zinc-400 hover:text-white transition-colors"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Newsletter Column (3 cols) */}
          <div className="lg:col-span-3 space-y-3">
            <h4 className="font-semibold text-xs text-white uppercase tracking-wider">
              {newsletterTitle}
            </h4>
            <p className="text-xs text-zinc-400 leading-relaxed">
              {newsletterSubtitle}
            </p>

            {isSubscribed ? (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-400 text-xs">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>Thanks for subscribing!</span>
              </div>
            ) : (
              <form onSubmit={handleSubscribe} className="space-y-2">
                <div className="flex gap-2">
                  <Input
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-zinc-900 border-zinc-800 text-white placeholder:text-zinc-500 text-xs h-9"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    disabled={isSubmitting}
                    className="h-9 px-3 shrink-0"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Copyright Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500">
          <p>{copyright}</p>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-zinc-300 transition-colors">
              Privacy Policy
            </a>
            <a href="#" className="hover:text-zinc-300 transition-colors">
              Terms of Service
            </a>
            <a href="#" className="hover:text-zinc-300 transition-colors">
              Cookie Settings
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
