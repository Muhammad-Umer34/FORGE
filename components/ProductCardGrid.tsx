// Showcase grid of product cards featuring photos, pricing, badges, descriptions, and custom enquiry action links

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ArrowRight, Package } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ProductCardItem {
  id: string
  name: string
  price?: string
  description?: string
  imageUrl?: string
  badge?: string
  href?: string
  buttonLabel?: string
}

export interface ProductCardGridProps {
  badgeText?: string
  title?: string
  subtitle?: string
  buttonLabel?: string
  products?: ProductCardItem[]
  onProductClick?: (product: ProductCardItem) => void
  className?: string
}

export function ProductCardGrid({
  badgeText = "Featured Products",
  title = "Explore Our Products",
  subtitle = "Discover our curated selection of high-quality items designed to meet your everyday needs.",
  buttonLabel = "Enquire",
  products = [
    {
      id: "prod-1",
      name: "Product Name One",
      price: "$29.00",
      description: "Brief summary describing the primary benefits and specifications of this product.",
      badge: "Best Seller",
      imageUrl: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
      href: "#contact",
    },
    {
      id: "prod-2",
      name: "Product Name Two",
      price: "$45.00",
      description: "Crafted with durable materials and precision design for outstanding performance.",
      imageUrl: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
      href: "#contact",
    },
    {
      id: "prod-3",
      name: "Product Name Three",
      price: "$19.50",
      description: "A popular favorite offering reliable quality and exceptional value.",
      badge: "New Arrival",
      imageUrl: "https://images.unsplash.com/photo-1572635196237-14b3f281503f?auto=format&fit=crop&w=600&q=80",
      href: "#contact",
    },
  ],
  onProductClick,
  className,
}: ProductCardGridProps) {
  if (!products || products.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <Package className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No products currently displayed.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="products" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
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

        {/* Product Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {products.map((product) => {
            const itemBtnLabel = product.buttonLabel || buttonLabel
            const itemHref = product.href || "#contact"

            return (
              <Card
                key={product.id}
                className="group flex flex-col justify-between overflow-hidden border-border bg-card hover:border-primary/40 hover:shadow-md transition-all duration-200"
              >
                <div>
                  {/* Image Container */}
                  <div className="relative aspect-square w-full bg-muted overflow-hidden">
                    {product.imageUrl ? (
                      <img
                        src={product.imageUrl}
                        alt={product.name}
                        className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center text-muted-foreground">
                        <Package className="h-12 w-12 opacity-30" />
                      </div>
                    )}
                    {product.badge && (
                      <div className="absolute top-3 left-3">
                        <Badge className="bg-primary text-primary-foreground shadow-sm text-xs font-semibold">
                          {product.badge}
                        </Badge>
                      </div>
                    )}
                  </div>

                  {/* Content Area */}
                  <CardContent className="p-6 space-y-3">
                    <div className="flex items-baseline justify-between gap-2">
                      <h3 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors">
                        {product.name}
                      </h3>
                      {product.price && (
                        <span className="font-extrabold text-primary text-base shrink-0">
                          {product.price}
                        </span>
                      )}
                    </div>
                    {product.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                        {product.description}
                      </p>
                    )}
                  </CardContent>
                </div>

                {/* Footer Action */}
                <div className="p-6 pt-0">
                  <Button
                    className="w-full justify-center gap-1.5"
                    onClick={() => onProductClick?.(product)}
                    asChild={!onProductClick}
                  >
                    {onProductClick ? (
                      <>
                        {itemBtnLabel} <ArrowRight className="h-3.5 w-3.5" />
                      </>
                    ) : (
                      <a href={itemHref}>
                        {itemBtnLabel} <ArrowRight className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
