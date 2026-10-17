// Restaurant menu or product catalog grid with category filters, item pricing, dietary tags, descriptions, and add-to-order action buttons

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Plus, Sparkles, ShoppingBag, Check } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CatalogItem {
  id?: string
  name: string
  description: string
  price: string
  category: string
  imageUrl?: string
  tags?: string[]
  isPopular?: boolean
}

export interface MenuCatalogGridProps {
  badgeText?: string
  title?: string
  subtitle?: string
  categories?: string[]
  items?: CatalogItem[]
  onItemOrder?: (item: CatalogItem) => void
  className?: string
}

export function MenuCatalogGrid({
  badgeText = "Menu & Offerings",
  title = "Artisanal Food & Beverage Selection",
  subtitle = "Crafted fresh daily with locally sourced organic ingredients, seasonal produce, and passion.",
  categories = ["All", "Main Course", "Appetizers", "Beverages", "Desserts"],
  items = [
    {
      id: "item-1",
      name: "Truffle Tagliatelle",
      description: "Handmade egg pasta tossed with black winter truffles, aged parmesan cream, and fresh herbs.",
      price: "$26.00",
      category: "Main Course",
      tags: ["Vegetarian", "Signature"],
      isPopular: true,
      imageUrl: "https://images.unsplash.com/photo-1556760544-74068565f05c?auto=format&fit=crop&w=400&q=80",
    },
    {
      id: "item-2",
      name: "Pan-Seared Sea Bass",
      description: "Crispy skin Mediterranean sea bass served over saffron risotto and roasted baby asparagus.",
      price: "$32.00",
      category: "Main Course",
      tags: ["Gluten-Free", "Chef's Pick"],
      imageUrl: "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=400&q=80",
    },
    {
      id: "item-3",
      name: "Burrata & Heirloom Salad",
      description: "Creamy pugliese burrata, heirloom tomatoes, basil oil, and aged Modena balsamic drizzle.",
      price: "$18.50",
      category: "Appetizers",
      tags: ["Organic", "Fresh"],
      imageUrl: "https://images.unsplash.com/photo-1592417817098-8f3d6eb22509?auto=format&fit=crop&w=400&q=80",
    },
    {
      id: "item-4",
      name: "Espresso Martini Royale",
      description: "Single-origin espresso, premium vodka, coffee liqueur, and dark chocolate shavings.",
      price: "$15.00",
      category: "Beverages",
      tags: ["Cocktail"],
      imageUrl: "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=400&q=80",
    },
    {
      id: "item-5",
      name: "Madagascar Vanilla Mille-Feuille",
      description: "Crisp caramelized puff pastry layered with light Tahitian vanilla bean mousseline.",
      price: "$14.00",
      category: "Desserts",
      tags: ["Sweet", "Artisan"],
      imageUrl: "https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&w=400&q=80",
    },
    {
      id: "item-6",
      name: "Charred Spanish Octopus",
      description: "Tender grilled octopus with smoked paprika potato puree and chimichurri emulsion.",
      price: "$22.00",
      category: "Appetizers",
      tags: ["Seafood"],
      imageUrl: "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=400&q=80",
    },
  ],
  onItemOrder,
  className,
}: MenuCatalogGridProps) {
  const [activeCategory, setActiveCategory] = useState("All")
  const [orderedItems, setOrderedItems] = useState<Record<string, boolean>>({})

  const filteredItems =
    activeCategory === "All"
      ? items
      : items.filter((item) => item.category === activeCategory)

  const handleOrder = (item: CatalogItem) => {
    const key = item.id || item.name
    setOrderedItems((prev) => ({ ...prev, [key]: true }))
    setTimeout(() => {
      setOrderedItems((prev) => ({ ...prev, [key]: false }))
    }, 1500)

    if (onItemOrder) {
      onItemOrder(item)
    }
  }

  return (
    <section
      id="menu"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
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

        {/* Categories Bar */}
        {categories && categories.length > 1 && (
          <div className="flex items-center justify-center flex-wrap gap-2 mb-10">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCategory(cat)}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-medium transition-colors duration-150",
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

        {/* 2-Column Responsive Item Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
          {filteredItems.map((item, idx) => {
            const key = item.id || item.name
            const isAdded = Boolean(orderedItems[key])

            return (
              <Card
                key={idx}
                className="overflow-hidden border-border bg-card shadow-sm hover:shadow-md transition-shadow rounded-2xl flex flex-col sm:flex-row justify-between p-4 sm:p-5 gap-4"
              >
                {/* Thumbnail Image */}
                {item.imageUrl && (
                  <div className="w-full sm:w-28 h-28 shrink-0 rounded-xl overflow-hidden bg-muted">
                    <img
                      src={item.imageUrl}
                      alt={item.name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                )}

                {/* Content */}
                <div className="flex-1 flex flex-col justify-between space-y-2">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-bold text-base text-foreground flex items-center gap-1.5">
                        <span>{item.name}</span>
                        {item.isPopular && (
                          <Badge variant="secondary" className="text-[10px] bg-primary/10 text-primary border-primary/20">
                            <Sparkles className="h-2.5 w-2.5 mr-0.5" /> Popular
                          </Badge>
                        )}
                      </h4>
                      <span className="font-extrabold text-foreground text-base shrink-0">
                        {item.price}
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-border/40">
                    <div className="flex flex-wrap gap-1">
                      {item.tags?.map((t, tIdx) => (
                        <span
                          key={tIdx}
                          className="px-2 py-0.5 rounded bg-muted text-[10px] text-muted-foreground font-medium"
                        >
                          {t}
                        </span>
                      ))}
                    </div>

                    <Button
                      size="sm"
                      variant={isAdded ? "secondary" : "outline"}
                      onClick={() => handleOrder(item)}
                      className={cn(
                        "h-8 px-3 text-xs gap-1 transition-all",
                        isAdded && "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950 dark:border-emerald-800"
                      )}
                    >
                      {isAdded ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                          Added
                        </>
                      ) : (
                        <>
                          <Plus className="h-3.5 w-3.5" />
                          Order
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
