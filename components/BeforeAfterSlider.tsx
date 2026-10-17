// Interactive before and after image comparison slider with touch drag, pointer tracking, and keyboard accessibility

"use client"

import React, { useState, useRef, useCallback, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { ChevronsLeftRight, ImageIcon } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SliderImageData {
  src: string
  alt?: string
  label?: string
}

export interface BeforeAfterSliderProps {
  badgeText?: string
  title?: string
  subtitle?: string
  beforeImage?: SliderImageData
  afterImage?: SliderImageData
  initialSliderPosition?: number // 0 to 100
  className?: string
}

export function BeforeAfterSlider({
  badgeText = "Visual Transformation",
  title = "Before & After Results",
  subtitle = "Drag the slider horizontally to view the before and after transformation.",
  beforeImage = {
    src: "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=80",
    alt: "Before state",
    label: "Before",
  },
  afterImage = {
    src: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
    alt: "After state",
    label: "After",
  },
  initialSliderPosition = 50,
  className,
}: BeforeAfterSliderProps) {
  const [sliderPos, setSliderPos] = useState(initialSliderPosition)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMove = useCallback((clientX: number) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const x = clientX - rect.left
    const percent = Math.min(Math.max((x / rect.width) * 100, 0), 100)
    setSliderPos(percent)
  }, [])

  // Mouse & Touch global listeners during drag
  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      handleMove(e.clientX)
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX)
      }
    }

    const handleEnd = () => {
      setIsDragging(false)
    }

    window.addEventListener("mousemove", handleMouseMove)
    window.addEventListener("mouseup", handleEnd)
    window.addEventListener("touchmove", handleTouchMove)
    window.addEventListener("touchend", handleEnd)

    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("mouseup", handleEnd)
      window.removeEventListener("touchmove", handleTouchMove)
      window.removeEventListener("touchend", handleEnd)
    }
  }, [isDragging, handleMove])

  // Keyboard accessibility
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault()
      setSliderPos((prev) => Math.max(0, prev - 5))
    } else if (e.key === "ArrowRight") {
      e.preventDefault()
      setSliderPos((prev) => Math.min(100, prev + 5))
    } else if (e.key === "Home") {
      e.preventDefault()
      setSliderPos(0)
    } else if (e.key === "End") {
      e.preventDefault()
      setSliderPos(100)
    }
  }

  if (!beforeImage?.src || !afterImage?.src) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <ImageIcon className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Comparison images are currently unavailable.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="transformation" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
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

        {/* Comparison Frame */}
        <div
          ref={containerRef}
          onMouseDown={(e) => {
            setIsDragging(true)
            handleMove(e.clientX)
          }}
          onTouchStart={(e) => {
            setIsDragging(true)
            if (e.touches.length > 0) handleMove(e.touches[0].clientX)
          }}
          className="relative aspect-[16/10] sm:aspect-[16/9] w-full rounded-2xl overflow-hidden bg-muted border border-border shadow-md select-none cursor-ew-resize"
        >
          {/* Base Layer: Before Image */}
          <img
            src={beforeImage.src}
            alt={beforeImage.alt || "Before comparison state"}
            className="absolute inset-0 h-full w-full object-cover pointer-events-none"
          />

          {/* Before Label Badge */}
          <div className="absolute top-4 left-4 z-10 pointer-events-none">
            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-black/70 backdrop-blur text-white border border-white/20">
              {beforeImage.label || "Before"}
            </span>
          </div>

          {/* Top Clipped Layer: After Image */}
          <div
            className="absolute inset-0 overflow-hidden pointer-events-none"
            style={{ width: `${sliderPos}%` }}
          >
            <img
              src={afterImage.src}
              alt={afterImage.alt || "After comparison state"}
              className="absolute inset-0 h-full w-full object-cover pointer-events-none max-w-none"
              style={{
                width: containerRef.current ? `${containerRef.current.clientWidth}px` : "100%",
                height: "100%",
              }}
            />
            {/* After Label Badge */}
            <div className="absolute top-4 left-4 z-10 pointer-events-none">
              <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary text-primary-foreground shadow-md">
                {afterImage.label || "After"}
              </span>
            </div>
          </div>

          {/* Draggable Divider Line & Thumb */}
          <div
            role="slider"
            tabIndex={0}
            aria-label="Image comparison divider"
            aria-valuenow={Math.round(sliderPos)}
            aria-valuemin={0}
            aria-valuemax={100}
            onKeyDown={handleKeyDown}
            className="absolute top-0 bottom-0 z-20 -translate-x-1/2 flex items-center justify-center cursor-ew-resize focus:outline-none"
            style={{ left: `${sliderPos}%` }}
          >
            {/* Vertical Line */}
            <div className="w-0.5 h-full bg-white shadow-[0_0_10px_rgba(0,0,0,0.5)]" />

            {/* Circular Handle */}
            <div
              className={cn(
                "absolute h-10 w-10 rounded-full bg-white text-zinc-900 shadow-xl flex items-center justify-center border-2 border-white/80 transition-transform",
                isDragging ? "scale-110" : "hover:scale-105",
                "focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-2"
              )}
            >
              <ChevronsLeftRight className="h-5 w-5 text-zinc-800" />
            </div>
          </div>
        </div>

        {/* Accessibility Instruction / Tip */}
        <p className="text-center text-xs text-muted-foreground mt-4">
          Use your mouse/finger to drag, or select the slider and press arrow keys (Left/Right) to adjust.
        </p>
      </div>
    </section>
  )
}
