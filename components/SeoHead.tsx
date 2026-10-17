// SEO helper providing Next.js metadata construction and client-side page title/meta synchronization

"use client"

import React, { useEffect } from "react"
import type { Metadata } from "next"

export interface SeoMetadataOptions {
  title?: string
  description?: string
  canonicalUrl?: string
  ogImageUrl?: string
  siteName?: string
  noIndex?: boolean
  keywords?: string[]
}

/**
 * Helper function to construct standard Next.js App Router Metadata objects
 * for use in server components or layout definitions.
 */
export function constructMetadata({
  title = "FORGE | Production Web Engine",
  description = "Turn natural language into high-converting small business websites.",
  canonicalUrl,
  ogImageUrl,
  siteName = "FORGE",
  noIndex = false,
  keywords = ["small business website", "ai web builder", "nextjs", "web generator"],
}: SeoMetadataOptions = {}): Metadata {
  return {
    title: {
      default: title,
      template: `%s | ${siteName}`,
    },
    description,
    keywords,
    metadataBase: canonicalUrl ? new URL(canonicalUrl) : undefined,
    alternates: canonicalUrl ? { canonical: canonicalUrl } : undefined,
    openGraph: {
      title,
      description,
      siteName,
      images: ogImageUrl ? [{ url: ogImageUrl }] : undefined,
      type: "website",
    },
    twitter: {
      card: ogImageUrl ? "summary_large_image" : "summary",
      title,
      description,
      images: ogImageUrl ? [ogImageUrl] : undefined,
    },
    robots: noIndex ? { index: false, follow: false } : { index: true, follow: true },
  }
}

export interface SeoHeadProps extends SeoMetadataOptions {
  children?: React.ReactNode
}

/**
 * Client component to dynamically update document title and meta tags on client transitions.
 */
export function SeoHead({
  title = "Page Title",
  description = "A comprehensive description of this page for search engine optimization.",
  canonicalUrl,
  ogImageUrl,
  noIndex = false,
  children,
}: SeoHeadProps) {
  useEffect(() => {
    if (typeof document !== "undefined") {
      if (title) {
        document.title = title
      }

      // Update meta description
      let metaDesc = document.querySelector('meta[name="description"]')
      if (!metaDesc && description) {
        metaDesc = document.createElement("meta")
        metaDesc.setAttribute("name", "description")
        document.head.appendChild(metaDesc)
      }
      if (metaDesc && description) {
        metaDesc.setAttribute("content", description)
      }

      // Update canonical link
      if (canonicalUrl) {
        let linkCanonical = document.querySelector('link[rel="canonical"]')
        if (!linkCanonical) {
          linkCanonical = document.createElement("link")
          linkCanonical.setAttribute("rel", "canonical")
          document.head.appendChild(linkCanonical)
        }
        linkCanonical.setAttribute("href", canonicalUrl)
      }

      // Robots meta tag
      if (noIndex) {
        let metaRobots = document.querySelector('meta[name="robots"]')
        if (!metaRobots) {
          metaRobots = document.createElement("meta")
          metaRobots.setAttribute("name", "robots")
          document.head.appendChild(metaRobots)
        }
        metaRobots.setAttribute("content", "noindex, nofollow")
      }
    }
  }, [title, description, canonicalUrl, noIndex])

  return children ? <>{children}</> : null
}
