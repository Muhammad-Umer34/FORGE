// Physical location showcase with address card, embedded interactive map iframe, and external directions link

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { MapPin, Navigation, ExternalLink, Building2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LocationMapProps {
  badgeText?: string
  title?: string
  subtitle?: string
  businessName?: string
  address?: string
  cityStateZip?: string
  additionalInfo?: string
  mapEmbedUrl?: string
  directionsUrl?: string
  directionsButtonText?: string
  className?: string
}

export function LocationMap({
  badgeText = "Find Us",
  title = "Visit Our Location",
  subtitle = "Stop by our storefront or office. We look forward to welcoming you.",
  businessName = "Our Business",
  address = "123 Business Boulevard, Suite 100",
  cityStateZip = "City, ST 12345",
  additionalInfo = "Convenient parking available on-site. Wheelchair accessible entrance.",
  mapEmbedUrl,
  directionsUrl,
  directionsButtonText = "Get Directions",
  className,
}: LocationMapProps) {
  const fullAddress = [address, cityStateZip].filter(Boolean).join(", ")
  const googleDirectionsUrl =
    directionsUrl ||
    (fullAddress ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(fullAddress)}` : "#")

  const hasMap = Boolean(mapEmbedUrl && mapEmbedUrl.trim().length > 0)

  return (
    <section id="location" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-3xl mx-auto text-center space-y-3 mb-12">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground">{subtitle}</p>}
        </div>

        {/* Layout Grid */}
        <div className={cn("grid gap-8 items-stretch", hasMap ? "grid-cols-1 lg:grid-cols-12" : "max-w-2xl mx-auto")}>
          {/* Address Details Card */}
          <div className={cn("flex flex-col justify-between", hasMap ? "lg:col-span-5" : "w-full")}>
            <Card className="h-full border-border bg-card shadow-sm flex flex-col justify-between p-6 sm:p-8">
              <div className="space-y-6">
                <div className="flex items-center gap-3 text-primary">
                  <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-foreground">{businessName}</h3>
                    <p className="text-xs text-muted-foreground">Primary Location</p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-muted/40 border border-border/60 space-y-2">
                  <div className="flex items-start gap-2.5 text-sm text-foreground">
                    <MapPin className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium">{address}</div>
                      {cityStateZip && <div className="text-muted-foreground text-xs mt-0.5">{cityStateZip}</div>}
                    </div>
                  </div>
                </div>

                {additionalInfo && (
                  <p className="text-xs text-muted-foreground leading-relaxed pl-1 border-l-2 border-primary/30">
                    {additionalInfo}
                  </p>
                )}
              </div>

              <div className="pt-6 mt-6 border-t border-border/60">
                <Button asChild className="w-full gap-2">
                  <a href={googleDirectionsUrl} target="_blank" rel="noopener noreferrer">
                    <Navigation className="h-4 w-4" />
                    {directionsButtonText}
                    <ExternalLink className="h-3.5 w-3.5 opacity-70 ml-auto" />
                  </a>
                </Button>
              </div>
            </Card>
          </div>

          {/* Map Embed Column */}
          {hasMap && (
            <div className="lg:col-span-7">
              <Card className="h-full min-h-[360px] sm:min-h-[420px] overflow-hidden border-border bg-muted/20 relative shadow-sm">
                <iframe
                  title={`Map showing location of ${businessName}`}
                  src={mapEmbedUrl}
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  loading="lazy"
                  allowFullScreen
                  referrerPolicy="no-referrer-when-downgrade"
                  className="w-full h-full min-h-[360px] sm:min-h-[420px] filter saturate-[0.95]"
                />
              </Card>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
