// Logo Cloud / Social Proof Strip: Monochromatic partner, accreditation, and press badge strip

"use client"

import React from "react"
import { ShieldCheck, Award, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LogoItem {
  name: string
  label?: string
}

export interface LogoCloudProps {
  title?: string
  logos?: LogoItem[]
  className?: string
}

export function LogoCloud({
  title = "Accredited & Certified by Recognized Industry Leaders",
  logos = [
    { name: "American Dental Association", label: "ADA Accredited" },
    { name: "Global Health Alliance", label: "GHA Certified" },
    { name: "Dental Board Certified", label: "State Licensed" },
    { name: "EcoHealth Practices", label: "Green Certified" },
    { name: "CareCredit Partner", label: "Financing Partner" },
  ],
  className,
}: LogoCloudProps) {
  return (
    <section
      id="logos"
      className={cn(
        "w-full py-10 sm:py-12 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {title && (
          <p className="text-xs uppercase tracking-wider font-semibold text-muted-foreground mb-8">
            {title}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-10 lg:gap-14 opacity-80 hover:opacity-100 transition-opacity">
          {logos.map((logo, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2.5 px-4 py-2 rounded-xl border border-border/50 bg-card/40 backdrop-blur hover:border-primary/40 transition-colors"
            >
              <div className="h-7 w-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div className="text-left">
                <div className="font-semibold text-xs text-foreground tracking-tight">
                  {logo.name}
                </div>
                {logo.label && (
                  <div className="text-[10px] text-muted-foreground">
                    {logo.label}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
