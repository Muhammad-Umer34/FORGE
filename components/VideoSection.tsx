// Click-to-load responsive video showcase with custom preview poster, play button, and caption support

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Play, Video } from "lucide-react"
import { cn } from "@/lib/utils"

export interface VideoSectionProps {
  badgeText?: string
  title?: string
  subtitle?: string
  videoUrl?: string
  thumbnailUrl?: string
  thumbnailAlt?: string
  caption?: string
  className?: string
}

function parseVideoEmbedUrl(url?: string): string {
  if (!url) return ""
  const trimmed = url.trim()

  // Already an embed URL
  if (trimmed.includes("/embed/")) {
    const separator = trimmed.includes("?") ? "&" : "?"
    return `${trimmed}${separator}autoplay=1`
  }

  // YouTube watch link
  const ytMatch = trimmed.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i)
  if (ytMatch && ytMatch[1]) {
    return `https://www.youtube.com/embed/${ytMatch[1]}?autoplay=1&rel=0`
  }

  // Vimeo link
  const vimeoMatch = trimmed.match(/vimeo\.com\/(?:channels\/(?:\w+\/)?|groups\/([^\/]*)\/videos\/|album\/(?:\d+)\/video\/|)(\d+)/)
  if (vimeoMatch && vimeoMatch[2]) {
    return `https://player.vimeo.com/video/${vimeoMatch[2]}?autoplay=1`
  }

  return trimmed
}

export function VideoSection({
  badgeText = "Video Spotlight",
  title = "See Our Work in Action",
  subtitle = "Watch a short documentary introducing our craft, workspace, and customer philosophy.",
  videoUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  thumbnailUrl = "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1400&q=80",
  thumbnailAlt = "Video thumbnail preview",
  caption = "Take a 2-minute tour behind the scenes with our founding team.",
  className,
}: VideoSectionProps) {
  const [isPlaying, setIsPlaying] = useState(false)

  if (!videoUrl) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <Video className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Video presentation is currently unavailable.</p>
        </div>
      </section>
    )
  }

  const embedSrc = parseVideoEmbedUrl(videoUrl)

  return (
    <section id="video" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
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

        {/* Video Player Frame */}
        <div className="relative aspect-video w-full rounded-2xl overflow-hidden bg-zinc-950 border border-border shadow-xl">
          {isPlaying ? (
            <iframe
              src={embedSrc}
              title={title}
              width="100%"
              height="100%"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              className="w-full h-full border-0"
            />
          ) : (
            <div className="relative w-full h-full group cursor-pointer" onClick={() => setIsPlaying(true)}>
              {/* Thumbnail Poster */}
              <img
                src={thumbnailUrl}
                alt={thumbnailAlt}
                className="w-full h-full object-cover filter brightness-75 group-hover:brightness-90 transition-all duration-300 group-hover:scale-102"
              />

              {/* Pulsing Play Button */}
              <div className="absolute inset-0 flex items-center justify-center">
                <button
                  type="button"
                  aria-label="Play video"
                  className={cn(
                    "h-20 w-20 rounded-full bg-primary/90 text-primary-foreground flex items-center justify-center shadow-2xl backdrop-blur",
                    "group-hover:scale-110 group-hover:bg-primary transition-all duration-200",
                    "focus:outline-none focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-4"
                  )}
                >
                  <Play className="h-8 w-8 ml-1 fill-current" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Caption */}
        {caption && (
          <p className="text-center text-xs sm:text-sm text-muted-foreground mt-4 max-w-2xl mx-auto leading-relaxed">
            {caption}
          </p>
        )}
      </div>
    </section>
  )
}
