// Single blog article detail template featuring hero visual, author byline, formatted reading body, and social share actions

"use client"

import React, { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Calendar, Clock, User, ArrowLeft, Share2, Check, Link2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface BlogPostAuthor {
  name: string
  title?: string
  avatarUrl?: string
  bio?: string
}

export interface BlogPostProps {
  title?: string
  subtitle?: string
  date?: string
  readTime?: string
  category?: string
  author?: BlogPostAuthor
  heroImageUrl?: string
  heroImageAlt?: string
  content?: string
  tags?: string[]
  shareUrl?: string
  backHref?: string
  backLabel?: string
  className?: string
}

export function BlogPost({
  title = "Article Title Goes Here",
  subtitle = "A detailed exploration of actionable strategies, best practices, and expert lessons.",
  date = "October 10, 2026",
  readTime = "6 min read",
  category = "Industry Insights",
  author = {
    name: "Author Name",
    title: "Senior Specialist & Founder",
    bio: "Passionate about helping small businesses optimize customer experiences and create lasting community impact.",
  },
  heroImageUrl = "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1400&q=80",
  heroImageAlt = "Article hero banner image",
  content = `When running a growing business, one of the most significant challenges is balancing daily operational execution with long-term strategic vision. Every day brings unexpected tasks, customer requests, and administrative responsibilities that can easily pull focus away from foundational growth.

In this guide, we break down three core pillars that create operational stability:

1. Clarifying Your Value Proposition: Customers should understand within three seconds what sets your business apart. Avoid technical jargon and speak directly to the tangible benefit you provide.

2. Establishing Dependable Communication Channels: Whether your clients prefer WhatsApp, phone consultations, or email confirmations, having clear response timeframes builds trust and eliminates friction.

3. Investing in Consistency over Novelty: Great brands are built on reliably delivering quality time and time again. Standardizing your service steps ensures every client receives the same high-touch experience.

By focusing on these core fundamentals, business owners can build a sustainable foundation that thrives across seasons.`,
  tags = ["Strategy", "Operations", "Best Practices"],
  shareUrl,
  backHref = "#blog",
  backLabel = "Back to All Articles",
  className,
}: BlogPostProps) {
  const [copied, setCopied] = useState(false)

  const handleCopyLink = () => {
    if (typeof window !== "undefined") {
      const url = shareUrl || window.location.href
      navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const paragraphs = (content || "").split("\n\n").filter(Boolean)

  return (
    <article className={cn("w-full py-12 sm:py-20 bg-background border-b border-border/40", className)}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        {/* Navigation Breadcrumb / Back Link */}
        <div>
          <a
            href={backHref}
            className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {backLabel}
          </a>
        </div>

        {/* Article Header */}
        <header className="space-y-4">
          {category && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {category}
            </Badge>
          )}

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-foreground leading-tight">
            {title}
          </h1>

          {subtitle && (
            <p className="text-base sm:text-lg text-muted-foreground leading-relaxed">
              {subtitle}
            </p>
          )}

          {/* Author Byline & Date Meta */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-border/60 text-xs text-muted-foreground">
            <div className="flex items-center gap-3">
              {author?.avatarUrl ? (
                <img
                  src={author.avatarUrl}
                  alt={author.name}
                  className="h-10 w-10 rounded-full object-cover"
                />
              ) : (
                <div className="h-10 w-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">
                  <User className="h-4 w-4" />
                </div>
              )}
              <div>
                <div className="font-semibold text-foreground text-sm">{author?.name}</div>
                {author?.title && <div>{author.title}</div>}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {date}
              </span>
              {readTime && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {readTime}
                  </span>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Hero Visual Image */}
        {heroImageUrl && (
          <div className="relative aspect-[16/9] w-full rounded-2xl overflow-hidden bg-muted border border-border shadow-md">
            <img
              src={heroImageUrl}
              alt={heroImageAlt || title}
              className="h-full w-full object-cover"
            />
          </div>
        )}

        {/* Body Content */}
        <div className="prose prose-zinc dark:prose-invert max-w-none space-y-6 text-foreground/90 leading-relaxed text-base sm:text-lg font-normal">
          {paragraphs.map((p, idx) => (
            <p key={idx} className="whitespace-pre-line">
              {p}
            </p>
          ))}
        </div>

        {/* Tags Row */}
        {tags && tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-6 border-t border-border/60">
            <span className="text-xs font-semibold text-muted-foreground mr-1">Tags:</span>
            {tags.map((tag) => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground border border-border"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Social Share Strip */}
        <div className="p-6 rounded-2xl bg-card border border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
            <Share2 className="h-4 w-4 text-primary" />
            <span>Share this article</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyLink}
              className="gap-1.5 text-xs"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Link2 className="h-3.5 w-3.5" />
                  Copy Link
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Author Bio Card */}
        {author && (
          <Card className="p-6 sm:p-8 border-border bg-muted/30 flex flex-col sm:flex-row gap-5 items-start">
            {author.avatarUrl ? (
              <img
                src={author.avatarUrl}
                alt={author.name}
                className="h-14 w-14 rounded-full object-cover shrink-0"
              />
            ) : (
              <div className="h-14 w-14 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <User className="h-6 w-6" />
              </div>
            )}
            <div className="space-y-1.5">
              <h3 className="font-bold text-foreground text-base">About {author.name}</h3>
              {author.title && <div className="text-xs text-primary font-medium">{author.title}</div>}
              {author.bio && <p className="text-sm text-muted-foreground leading-relaxed">{author.bio}</p>}
            </div>
          </Card>
        )}
      </div>
    </article>
  )
}
