// Blog post overview grid or list with category filter chips, author metadata, read time, and excerpt cards

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Calendar, Clock, User, ArrowRight, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

export interface BlogPostItem {
  id: string
  title: string
  date: string
  excerpt: string
  author?: {
    name: string
    avatarUrl?: string
  }
  category?: string
  imageUrl?: string
  href?: string
  readTime?: string
}

export interface BlogListProps {
  badgeText?: string
  title?: string
  subtitle?: string
  categories?: string[]
  posts?: BlogPostItem[]
  layout?: "grid" | "list"
  className?: string
}

export function BlogList({
  badgeText = "Our Journal",
  title = "Latest Articles & Insights",
  subtitle = "Practical advice, industry thoughts, and helpful resources written by our team.",
  categories = ["All", "Guides", "Announcements", "Tips"],
  posts = [
    {
      id: "post-1",
      title: "Essential Tips for Growing Your Local Customer Base",
      date: "October 10, 2026",
      excerpt: "Learn practical approaches to improving customer retention and local community visibility without a massive advertising budget.",
      author: { name: "Author Name" },
      category: "Guides",
      readTime: "5 min read",
      imageUrl: "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=600&q=80",
      href: "#",
    },
    {
      id: "post-2",
      title: "Streamlining Operations: A Step-by-Step Modern Playbook",
      date: "September 28, 2026",
      excerpt: "How small businesses can adopt modern digital workflows to eliminate repetitive administrative overhead.",
      author: { name: "Author Name" },
      category: "Tips",
      readTime: "4 min read",
      imageUrl: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=600&q=80",
      href: "#",
    },
    {
      id: "post-3",
      title: "Announcing Our Seasonal Service Offerings",
      date: "September 15, 2026",
      excerpt: "A preview of newly introduced packages and customized client consultations launching this season.",
      author: { name: "Author Name" },
      category: "Announcements",
      readTime: "3 min read",
      imageUrl: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=600&q=80",
      href: "#",
    },
  ],
  layout = "grid",
  className,
}: BlogListProps) {
  const [selectedCategory, setSelectedCategory] = useState("All")

  const filteredPosts = (posts || []).filter((post) => {
    if (selectedCategory === "All") return true
    return post.category?.toLowerCase() === selectedCategory.toLowerCase()
  })

  if (!posts || posts.length === 0) {
    return (
      <section className={cn("w-full py-16 bg-background border-b border-border/40 text-center", className)}>
        <div className="max-w-md mx-auto px-4 text-muted-foreground">
          <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No articles currently published.</p>
        </div>
      </section>
    )
  }

  return (
    <section id="blog" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
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

        {/* Category Filter Chips */}
        {categories && categories.length > 1 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mb-12">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                  selectedCategory.toLowerCase() === cat.toLowerCase()
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80"
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {/* Posts Display */}
        {filteredPosts.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground text-sm">
            No articles found matching the &quot;{selectedCategory}&quot; category.
          </div>
        ) : layout === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredPosts.map((post) => (
              <Card
                key={post.id}
                className="group flex flex-col justify-between overflow-hidden border-border bg-card hover:border-primary/40 hover:shadow-md transition-all duration-200"
              >
                <div>
                  {/* Article Thumbnail */}
                  {post.imageUrl && (
                    <div className="relative aspect-[16/10] w-full bg-muted overflow-hidden">
                      <img
                        src={post.imageUrl}
                        alt={post.title}
                        className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                      {post.category && (
                        <div className="absolute top-3 left-3">
                          <Badge className="bg-background/90 backdrop-blur text-foreground border border-border shadow-sm text-xs font-medium">
                            {post.category}
                          </Badge>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Body Content */}
                  <CardContent className="p-6 space-y-3">
                    {/* Meta line */}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {post.date}
                      </span>
                      {post.readTime && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {post.readTime}
                          </span>
                        </>
                      )}
                    </div>

                    <h3 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors line-clamp-2">
                      <a href={post.href || "#"}>{post.title}</a>
                    </h3>

                    <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
                      {post.excerpt}
                    </p>
                  </CardContent>
                </div>

                {/* Card Footer */}
                <div className="p-6 pt-0 border-t border-border/40 mt-auto flex items-center justify-between text-xs">
                  {post.author && (
                    <div className="flex items-center gap-2 text-foreground font-medium">
                      {post.author.avatarUrl ? (
                        <img
                          src={post.author.avatarUrl}
                          alt={post.author.name}
                          className="h-6 w-6 rounded-full object-cover"
                        />
                      ) : (
                        <div className="h-6 w-6 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                          <User className="h-3.5 w-3.5" />
                        </div>
                      )}
                      <span>{post.author.name}</span>
                    </div>
                  )}
                  <a
                    href={post.href || "#"}
                    className="inline-flex items-center gap-1 text-primary font-semibold hover:underline ml-auto"
                  >
                    Read article <ArrowRight className="h-3 w-3" />
                  </a>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          /* List layout */
          <div className="divide-y divide-border/60 max-w-4xl mx-auto">
            {filteredPosts.map((post) => (
              <article key={post.id} className="py-6 first:pt-0 last:pb-0 flex flex-col sm:flex-row gap-6 items-start">
                {post.imageUrl && (
                  <div className="w-full sm:w-48 aspect-[16/10] sm:aspect-square rounded-xl bg-muted overflow-hidden shrink-0">
                    <img src={post.imageUrl} alt={post.title} className="h-full w-full object-cover" />
                  </div>
                )}
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {post.category && <span className="font-semibold text-primary">{post.category}</span>}
                    <span>{post.date}</span>
                    {post.readTime && <span>• {post.readTime}</span>}
                  </div>
                  <h3 className="text-xl font-bold text-foreground hover:text-primary transition-colors">
                    <a href={post.href || "#"}>{post.title}</a>
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{post.excerpt}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
