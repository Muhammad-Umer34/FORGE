// Product spotlight page layout with gallery thumbnail switcher, variant attribute selectors, and direct enquiry action button

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ArrowRight, Check, Package, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ProductVariantGroup {
  name: string // e.g. "Size", "Flavour"
  options: string[] // e.g. ["Small (6\")", "Medium (8\")", "Large (10\")"]
}

export interface ProductDetailProps {
  name?: string
  price?: string
  originalPrice?: string
  badge?: string
  description?: string
  images?: { src: string; alt?: string }[]
  variants?: ProductVariantGroup[]
  enquireButtonText?: string
  onEnquire?: (selectedVariants: Record<string, string>) => void
  enquireHref?: string
  specifications?: { label: string; value: string }[]
  className?: string
}

export function ProductDetail({
  name = "Handcrafted Signature Loaf",
  price = "$14.50",
  originalPrice,
  badge = "Customer Favorite",
  description = "Naturally fermented over 36 hours using organic heirloom grains, spring water, and fine sea salt. Baked on traditional granite hearth stones for an exceptionally crisp crust and tender, custard-like interior crumb.",
  images = [
    {
      src: "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1000&q=80",
      alt: "Signature loaf front angle",
    },
    {
      src: "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=1000&q=80",
      alt: "Loaf cross section slice",
    },
    {
      src: "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?auto=format&fit=crop&w=1000&q=80",
      alt: "Loaves baking in the hearth",
    },
  ],
  variants = [
    { name: "Size", options: ["Standard (750g)", "Large Boule (1kg)"] },
    { name: "Flavour Style", options: ["Classic Country White", "Seeded Multigrain", "Roasted Garlic & Herb"] },
  ],
  enquireButtonText = "Enquire About Availability",
  onEnquire,
  enquireHref = "#contact",
  specifications = [
    { label: "Fermentation Time", value: "36 Hours Cold Proof" },
    { label: "Ingredients", value: "100% Organic Flours, Sea Salt, Water" },
    { label: "Dietary", value: "Vegan, Naturally Leavened" },
    { label: "Freshness Window", value: "Best consumed within 4–5 days" },
  ],
  className,
}: ProductDetailProps) {
  const [selectedImgIdx, setSelectedImgIdx] = useState(0)
  const [selectedVariants, setSelectedVariants] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    variants?.forEach((v) => {
      if (v.options && v.options.length > 0) {
        initial[v.name] = v.options[0]
      }
    })
    return initial
  })

  const currentImage = images?.[selectedImgIdx] || images?.[0]

  const handleVariantSelect = (groupName: string, option: string) => {
    setSelectedVariants((prev) => ({ ...prev, [groupName]: option }))
  }

  const handleEnquireClick = () => {
    if (onEnquire) {
      onEnquire(selectedVariants)
    }
  }

  return (
    <section id="product-detail" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          {/* Gallery View (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            {/* Primary Large Image */}
            <div className="relative aspect-square w-full rounded-2xl overflow-hidden bg-muted border border-border shadow-md">
              {currentImage?.src ? (
                <img
                  src={currentImage.src}
                  alt={currentImage.alt || name}
                  className="h-full w-full object-cover transition-all duration-300"
                />
              ) : (
                <div className="h-full w-full flex items-center justify-center text-muted-foreground">
                  <Package className="h-16 w-16 opacity-30" />
                </div>
              )}
              {badge && (
                <div className="absolute top-4 left-4">
                  <Badge className="bg-primary text-primary-foreground shadow-sm text-xs font-semibold">
                    {badge}
                  </Badge>
                </div>
              )}
            </div>

            {/* Thumbnails Row */}
            {images && images.length > 1 && (
              <div className="flex gap-3 overflow-x-auto pb-2">
                {images.map((img, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedImgIdx(idx)}
                    className={cn(
                      "relative h-20 w-20 rounded-xl overflow-hidden bg-muted border-2 shrink-0 transition-all",
                      selectedImgIdx === idx
                        ? "border-primary shadow-sm scale-102"
                        : "border-transparent opacity-70 hover:opacity-100"
                    )}
                  >
                    <img src={img.src} alt={img.alt || name} className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Product Details & Selectors (6 cols) */}
          <div className="lg:col-span-6 space-y-6">
            <div>
              <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">{name}</h1>
              <div className="flex items-baseline gap-3 mt-3">
                <span className="text-2xl sm:text-3xl font-black text-primary tabular-nums">{price}</span>
                {originalPrice && (
                  <span className="text-sm text-muted-foreground line-through tabular-nums">
                    {originalPrice}
                  </span>
                )}
              </div>
            </div>

            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
              {description}
            </p>

            {/* Variant Selectors */}
            {variants && variants.length > 0 && (
              <div className="space-y-4 pt-4 border-t border-border/60">
                {variants.map((group) => (
                  <div key={group.name} className="space-y-2">
                    <div className="text-xs font-semibold text-foreground flex justify-between">
                      <span>{group.name}:</span>
                      <span className="text-primary">{selectedVariants[group.name]}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {group.options.map((opt) => {
                        const isSelected = selectedVariants[group.name] === opt
                        return (
                          <button
                            key={opt}
                            type="button"
                            onClick={() => handleVariantSelect(group.name, opt)}
                            className={cn(
                              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all border",
                              isSelected
                                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                                : "bg-card text-foreground border-border hover:bg-muted"
                            )}
                          >
                            {opt}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Action Button */}
            <div className="pt-4">
              <Button
                size="lg"
                onClick={handleEnquireClick}
                asChild={!onEnquire}
                className="w-full justify-center gap-2 text-base font-bold h-12 shadow-md"
              >
                {onEnquire ? (
                  <>
                    {enquireButtonText} <ArrowRight className="h-4 w-4" />
                  </>
                ) : (
                  <a href={enquireHref}>
                    {enquireButtonText} <ArrowRight className="h-4 w-4" />
                  </a>
                )}
              </Button>
            </div>

            {/* Specifications List */}
            {specifications && specifications.length > 0 && (
              <div className="pt-6 border-t border-border/60 space-y-2">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Specifications & Highlights</h4>
                <div className="divide-y divide-border/40 text-xs">
                  {specifications.map((spec, idx) => (
                    <div key={idx} className="py-2 flex justify-between gap-4">
                      <span className="text-muted-foreground">{spec.label}</span>
                      <span className="font-medium text-foreground text-right">{spec.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
