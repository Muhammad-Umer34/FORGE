// Navigation header with brand logo, customizable navigation links, CTA action button, and responsive mobile hamburger menu

"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Menu, X, ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"

export interface NavLink {
  label: string
  href: string
}

export interface NavbarProps {
  brandName?: string
  logoUrl?: string
  links?: NavLink[]
  ctaText?: string
  ctaHref?: string
  onCtaClick?: () => void
  isSticky?: boolean
  className?: string
}

export function Navbar({
  brandName = "FORGE",
  logoUrl,
  links = [
    { label: "Features", href: "#features" },
    { label: "About", href: "#about" },
    { label: "Pricing", href: "#pricing" },
    { label: "Contact", href: "#contact" },
  ],
  ctaText = "Get Started",
  ctaHref = "#get-started",
  onCtaClick,
  isSticky = true,
  className,
}: NavbarProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  return (
    <header
      className={cn(
        "w-full bg-background/95 backdrop-blur border-b border-border transition-all z-40",
        isSticky ? "sticky top-0" : "relative",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Name */}
        <a href="#" className="flex items-center gap-2 font-bold text-lg text-foreground hover:opacity-90 transition-opacity">
          {logoUrl ? (
            <img src={logoUrl} alt={brandName} className="h-8 w-8 object-contain rounded" />
          ) : (
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-black text-sm">
              {brandName.charAt(0)}
            </div>
          )}
          <span>{brandName}</span>
        </a>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-muted-foreground">
          {links.map((link, idx) => (
            <a
              key={idx}
              href={link.href}
              className="hover:text-foreground transition-colors duration-150 py-1"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop Call to Action */}
        <div className="hidden md:flex items-center gap-3">
          {ctaText && (
            <Button
              size="sm"
              onClick={onCtaClick}
              asChild={!onCtaClick && Boolean(ctaHref)}
              className="gap-1.5"
            >
              {onCtaClick ? (
                <>
                  {ctaText} <ArrowRight className="h-3.5 w-3.5" />
                </>
              ) : (
                <a href={ctaHref}>
                  {ctaText} <ArrowRight className="h-3.5 w-3.5" />
                </a>
              )}
            </Button>
          )}
        </div>

        {/* Mobile Menu Toggle Button */}
        <div className="flex md:hidden items-center">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle navigation menu"
            className="h-9 w-9 text-foreground"
          >
            {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-background px-4 pt-2 pb-6 space-y-3 shadow-lg animate-in slide-in-from-top-2 duration-200">
          <nav className="flex flex-col space-y-2">
            {links.map((link, idx) => (
              <a
                key={idx}
                href={link.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className="px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>
          {ctaText && (
            <div className="pt-2 border-t border-border/60">
              <Button
                className="w-full justify-center gap-2"
                onClick={() => {
                  setIsMobileMenuOpen(false)
                  if (onCtaClick) onCtaClick()
                }}
                asChild={!onCtaClick && Boolean(ctaHref)}
              >
                {onCtaClick ? (
                  <>
                    {ctaText} <ArrowRight className="h-4 w-4" />
                  </>
                ) : (
                  <a href={ctaHref}>
                    {ctaText} <ArrowRight className="h-4 w-4" />
                  </a>
                )}
              </Button>
            </div>
          )}
        </div>
      )}
    </header>
  )
}
