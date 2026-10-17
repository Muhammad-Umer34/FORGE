// Interactive media image carousel with arrow controls, navigation dots, touch swipe, keyboard navigation, and motion-respecting autoplay

"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, ImageIcon } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CarouselImage {
  id: string
  src: string
  alt: string
  title?: string
  caption?: string
  tag?: string
}

export interface GalleryCarouselProps {
  badgeText?: string
  title?: string
  subtitle?: string
  images?: CarouselImage[]
  autoplay?: boolean
  autoplayInterval?: number
  className?: string
}

export function GalleryCarousel({
  badgeText = "Visual Showcase",
  title = "Explore Our Gallery",
  subtitle = "Swipe or click through our featured collection of high-resolution photographs.",
  images = [
    {
      id: "img-1",
      src: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80",
      alt: "Modern workspace interior",
      title: "Workspace & Collaboration Area",
      caption: "Thoughtfully crafted spaces designed for creative teamwork and focus.",
      tag: "Interior",
    },
    {
      id: "img-2",
      src: "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1200&q=80",
      alt: "Open architecture studio",
      title: "Design Studio & Production",
      caption: "Equipped with state-of-the-art tools and natural lighting.",
      tag: "Studio",
    },
    {
      id: "img-3",
      src: "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1200&q=80",
      alt: "Team strategy meeting",
      title: "Client Consultation Suite",
      caption: "Private discussion rooms dedicated to understanding client vision.",
      tag: "Consultation",
    },
  ],
  autoplay = true,
  autoplayInterval = 5000,
  className,
}: GalleryCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const touchStartXRef = useRef<number | null>(null)
  const touchEndXRef = useRef<number | null>(null)

  const count = images ? images.length : 0

  const handleNext = useCallback(() => {
    if (count <= 1) return
    setCurrentIndex((prev) => (prev + 1) % count)
  }, [count])

  const handlePrev = useCallback(() => {
    if (count <= 1) return
    setCurrentIndex((prev) => (prev - 1 + count) % count)
  }, [count])

  // Autoplay timer with prefers-reduced-motion check
  useEffect(() => {
    if (!autoplay || isPaused || count <= 1) return

    // Check prefers-reduced-motion
    if (typeof window !== "undefined") {
      const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)")
      if (mediaQuery.matches) return
    }

    const timer = setInterval(() => {
      handleNext()
    }, autoplayInterval)

    return () => clearInterval(timer)
  }, [autoplay, isPaused, count, autoplayInterval, handleNext])

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault()
      handlePrev()
    } else if (e.key === "ArrowRight") {
      e.preventDefault()
      handleNext()
    }
  }

  // Touch Swipe handlers
  const onTouchStart = (e: React.TouchEvent) => {
    touchStartXRef.current = e.targetTouches[0].clientX
    touchEndXRef.current = null
  }

  const onTouchMove = (e: React.TouchEvent) => {
    touchEndXRef.current = e.targetTouches[0].clientX
  }

  const onTouchEnd = () => {
    if (touchStartXRef.current === null || touchEndXRef.current === null) return
    const diff = touchStartXRef.current - touchEndXRef.current
    const minSwipeDistance = 40

    if (diff > minSwipeDistance) {
      handleNext()
    } else if (diff < -minSwipeDistance) {
      handlePrev()
    }

    touchStartXRef.current = null
    touchEndXRef.current = null
  }

  if (!images || images.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <ImageIcon className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No images currently in the gallery.</p>
        </div>
      </section>
    )
  }

  const currentImage = images[currentIndex]

  return (
    <section id="gallery" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-3xl mx-auto text-center space-y-3 mb-10">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground">{subtitle}</p>}
        </div>

        {/* Carousel Frame */}
        <div
          tabIndex={0}
          role="region"
          aria-label="Image Carousel"
          onKeyDown={handleKeyDown}
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
          onFocus={() => setIsPaused(true)}
          onBlur={() => setIsPaused(false)}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          className="relative rounded-2xl overflow-hidden border border-border bg-card shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        >
          {/* Main Visual Display */}
          <div className="relative aspect-video sm:aspect-[21/9] w-full bg-muted overflow-hidden">
            <img
              src={currentImage.src}
              alt={currentImage.alt}
              className="h-full w-full object-cover transition-opacity duration-300"
            />
            {/* Gradient Overlay for Caption Text */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent flex flex-col justify-end p-6 sm:p-10 text-white">
              {currentImage.tag && (
                <div className="mb-2">
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 backdrop-blur-md text-white border border-white/20">
                    {currentImage.tag}
                  </span>
                </div>
              )}
              {currentImage.title && (
                <h3 className="text-lg sm:text-2xl font-bold tracking-tight text-white mb-1">
                  {currentImage.title}
                </h3>
              )}
              {currentImage.caption && (
                <p className="text-xs sm:text-sm text-zinc-300 max-w-2xl leading-relaxed">
                  {currentImage.caption}
                </p>
              )}
            </div>
          </div>

          {/* Navigation Arrows */}
          {count > 1 && (
            <>
              <Button
                variant="outline"
                size="icon"
                onClick={handlePrev}
                aria-label="Previous slide"
                className="absolute left-4 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-background/80 hover:bg-background backdrop-blur shadow-md text-foreground border-border"
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={handleNext}
                aria-label="Next slide"
                className="absolute right-4 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-background/80 hover:bg-background backdrop-blur shadow-md text-foreground border-border"
              >
                <ChevronRight className="h-5 w-5" />
              </Button>
            </>
          )}

          {/* Slide Indicator Dots */}
          {count > 1 && (
            <div className="absolute bottom-4 right-6 flex items-center gap-1.5 z-10">
              {images.map((img, idx) => (
                <button
                  key={img.id}
                  type="button"
                  onClick={() => setCurrentIndex(idx)}
                  aria-label={`Go to slide ${idx + 1}`}
                  aria-current={idx === currentIndex ? "true" : undefined}
                  className={cn(
                    "h-2 rounded-full transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                    idx === currentIndex
                      ? "w-6 bg-white"
                      : "w-2 bg-white/50 hover:bg-white/70"
                  )}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
