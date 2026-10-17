// Responsive image gallery with categorized filter tabs, responsive multi-column grid, and interactive image lightbox dialog

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { ZoomIn, Image as ImageIcon } from "lucide-react"

export interface GalleryItem {
  url: string
  alt: string
  title?: string
  category?: string
  caption?: string
}

export interface ImageGalleryProps {
  badgeText?: string
  title?: string
  subtitle?: string
  categories?: string[]
  items?: GalleryItem[]
  className?: string
}

export function ImageGallery({
  badgeText = "Visual Gallery",
  title = "Explore Our Creative Showcase",
  subtitle = "High-resolution curated imagery showcasing creative work, architectural designs, and product interfaces.",
  categories = ["All", "Architecture", "Design", "Nature", "Technology"],
  items = [
    {
      url: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80",
      alt: "Modern architecture skyscraper",
      title: "Urban Skyline",
      category: "Architecture",
      caption: "Sleek glass high-rise reflecting the morning light.",
    },
    {
      url: "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80",
      alt: "Circuit board macro",
      title: "Neural Hardware",
      category: "Technology",
      caption: "High-density microchip architecture in development.",
    },
    {
      url: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
      alt: "Tropical beach with waves",
      title: "Coastal Breeze",
      category: "Nature",
      caption: "Pristine sandy shoreline under azure skies.",
    },
    {
      url: "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&w=800&q=80",
      alt: "Minimalist interior design",
      title: "Minimal Living",
      category: "Design",
      caption: "Clean Scandinavian aesthetics and organic textures.",
    },
    {
      url: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80",
      alt: "Matrix of code on screen",
      title: "Code Synthesis",
      category: "Technology",
      caption: "Real-time generative algorithms and code compiling.",
    },
    {
      url: "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=800&q=80",
      alt: "Foggy mountain peaks",
      title: "Alpine Mist",
      category: "Nature",
      caption: "Atmospheric cloud layers hovering above evergreen valleys.",
    },
  ],
  className,
}: ImageGalleryProps) {
  const [activeCategory, setActiveCategory] = useState("All")
  const [selectedImage, setSelectedImage] = useState<GalleryItem | null>(null)

  const filteredItems =
    activeCategory === "All"
      ? items
      : items.filter((item) => item.category === activeCategory)

  return (
    <section
      id="gallery"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-10">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            {title}
          </h2>
          {subtitle && (
            <p className="text-base text-muted-foreground leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {/* Category Filters */}
        {categories && categories.length > 1 && (
          <div className="flex items-center justify-center flex-wrap gap-2 mb-8">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCategory(cat)}
                className={cn(
                  "px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors duration-150",
                  activeCategory === cat
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {/* Gallery Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {filteredItems.map((item, idx) => (
            <div
              key={idx}
              onClick={() => setSelectedImage(item)}
              className="group relative rounded-xl overflow-hidden border border-border bg-card shadow-sm cursor-pointer hover:shadow-lg transition-all duration-200"
            >
              <div className="aspect-4/3 overflow-hidden bg-muted relative">
                <img
                  src={item.url}
                  alt={item.alt}
                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center text-white">
                  <div className="flex items-center gap-1.5 bg-black/60 backdrop-blur px-3 py-1.5 rounded-full text-xs font-medium">
                    <ZoomIn className="h-3.5 w-3.5" />
                    <span>View</span>
                  </div>
                </div>
              </div>

              {(item.title || item.category) && (
                <div className="p-4 flex items-center justify-between border-t border-border/60">
                  <div>
                    {item.title && (
                      <h4 className="font-semibold text-sm text-foreground">
                        {item.title}
                      </h4>
                    )}
                    {item.caption && (
                      <p className="text-xs text-muted-foreground line-clamp-1">
                        {item.caption}
                      </p>
                    )}
                  </div>
                  {item.category && (
                    <Badge variant="secondary" className="text-[10px]">
                      {item.category}
                    </Badge>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Lightbox Dialog Modal */}
        <Dialog
          open={Boolean(selectedImage)}
          onOpenChange={(open) => !open && setSelectedImage(null)}
        >
          {selectedImage && (
            <DialogContent className="max-w-3xl p-2 sm:p-4 bg-background border-border">
              <DialogTitle className="sr-only">
                {selectedImage.title || selectedImage.alt}
              </DialogTitle>
              <div className="space-y-3">
                <div className="rounded-lg overflow-hidden bg-black flex items-center justify-center max-h-[70vh]">
                  <img
                    src={selectedImage.url}
                    alt={selectedImage.alt}
                    className="max-h-[70vh] w-auto object-contain"
                  />
                </div>
                <div className="px-2 pb-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-base text-foreground">
                      {selectedImage.title || selectedImage.alt}
                    </h3>
                    {selectedImage.category && (
                      <Badge variant="outline">{selectedImage.category}</Badge>
                    )}
                  </div>
                  {selectedImage.caption && (
                    <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                      {selectedImage.caption}
                    </p>
                  )}
                </div>
              </div>
            </DialogContent>
          )}
        </Dialog>
      </div>
    </section>
  )
}
