// Portfolio and case studies showcase grid with category filters, project preview cards, tags, and project links

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ExternalLink, Layers, ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"

export interface PortfolioProject {
  title: string
  client?: string
  description: string
  imageUrl: string
  category?: string
  tags: string[]
  projectUrl?: string
}

export interface PortfolioGridProps {
  badgeText?: string
  title?: string
  subtitle?: string
  categories?: string[]
  projects?: PortfolioProject[]
  className?: string
}

export function PortfolioGrid({
  badgeText = "Featured Work",
  title = "Selected Projects & Client Case Studies",
  subtitle = "Explore modern web applications, design systems, and digital platforms crafted with high performance in mind.",
  categories = ["All", "Web App", "AI Integration", "E-Commerce", "Branding"],
  projects = [
    {
      title: "Nova Financial Intelligence",
      client: "Nova Corp",
      category: "Web App",
      description: "Real-time algorithmic trading dashboard with millisecond streaming data and customizable charting canvas.",
      imageUrl: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80",
      tags: ["Next.js", "TypeScript", "Tailwind", "WebSockets"],
      projectUrl: "https://example.com/project-1",
    },
    {
      title: "Synthetix AI Studio",
      client: "Synthetix Labs",
      category: "AI Integration",
      description: "Generative prompt playground allowing automated marketing copy creation, asset generation, and SEO analysis.",
      imageUrl: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80",
      tags: ["OpenAI", "React", "Radix UI", "Node.js"],
      projectUrl: "https://example.com/project-2",
    },
    {
      title: "Lumina Luxury Goods",
      client: "Lumina Retail",
      category: "E-Commerce",
      description: "Immersive headless e-commerce store with 3D product previews, instant checkout, and personalized recommendations.",
      imageUrl: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=800&q=80",
      tags: ["Shopify", "Tailwind CSS", "Stripe", "Next.js"],
      projectUrl: "https://example.com/project-3",
    },
  ],
  className,
}: PortfolioGridProps) {
  const [activeCategory, setActiveCategory] = useState("All")

  const filteredProjects =
    activeCategory === "All"
      ? projects
      : projects.filter((p) => p.category === activeCategory)

  return (
    <section
      id="portfolio"
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

        {/* Filter Pills */}
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

        {/* Projects Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredProjects.map((project, idx) => (
            <Card
              key={idx}
              className="group overflow-hidden border-border bg-card shadow-sm hover:shadow-xl transition-all duration-300 rounded-2xl flex flex-col justify-between"
            >
              <div>
                {/* Image Container */}
                <div className="aspect-16/10 overflow-hidden bg-muted relative">
                  <img
                    src={project.imageUrl}
                    alt={project.title}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    loading="lazy"
                  />
                  {project.category && (
                    <div className="absolute top-3 right-3">
                      <Badge className="bg-background/90 text-foreground backdrop-blur border shadow-sm text-xs">
                        {project.category}
                      </Badge>
                    </div>
                  )}
                </div>

                <CardContent className="p-6 space-y-3">
                  {project.client && (
                    <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                      {project.client}
                    </p>
                  )}
                  <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors flex items-center justify-between">
                    <span>{project.title}</span>
                    <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
                  </h3>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    {project.description}
                  </p>
                </CardContent>
              </div>

              {/* Tags & Action Link Footer */}
              <div className="px-6 pb-6 pt-2 border-t border-border/40 flex items-center justify-between flex-wrap gap-2">
                <div className="flex flex-wrap gap-1.5">
                  {project.tags.map((tag, tIdx) => (
                    <span
                      key={tIdx}
                      className="px-2 py-0.5 rounded bg-muted text-[11px] text-muted-foreground font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {project.projectUrl && (
                  <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="gap-1 text-xs text-foreground p-0 h-auto font-medium hover:text-primary"
                  >
                    <a
                      href={project.projectUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      View Case Study &rarr;
                    </a>
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
