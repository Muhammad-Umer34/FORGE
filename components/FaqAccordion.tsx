// Frequently asked questions FAQ accordion with collapsible question items, answers, and support help contact link

"use client"

import React from "react"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { HelpCircle, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface FaqItem {
  question: string
  answer: string
}

export interface FaqAccordionProps {
  badgeText?: string
  title?: string
  subtitle?: string
  items?: FaqItem[]
  contactText?: string
  contactHref?: string
  className?: string
}

export function FaqAccordion({
  badgeText = "Got Questions?",
  title = "Frequently Asked Questions",
  subtitle = "Everything you need to know about FORGE, WebContainers, generated code ownership, and custom deployments.",
  items = [
    {
      question: "How does the in-browser WebContainers engine work?",
      answer:
        "WebContainers run a complete Node.js runtime directly within modern browser tabs via WebAssembly and SharedArrayBuffer. This means Next.js compiles and runs locally on your machine with near-zero latency and zero remote server execution cost.",
    },
    {
      question: "Can I download and export the generated source code?",
      answer:
        "Yes! Every generated project exports as a standard Next.js application with TypeScript, Tailwind CSS, and shadcn/ui components. There are no proprietary runtime dependencies or vendor lock-in.",
    },
    {
      question: "How does the AI select and configure sections?",
      answer:
        "The AI leverages high-level component descriptions and semantic prompt understanding to pick matching section modules from our library, dynamically populating props like headlines, feature lists, pricing tiers, and contact forms.",
    },
    {
      question: "Is the generated website responsive across all mobile devices?",
      answer:
        "Every section in our library is built mobile-first using Tailwind CSS utility classes and verified across mobile (390px), tablet (768px), and full desktop viewports.",
    },
    {
      question: "Can I connect my own custom API backend or database?",
      answer:
        "Yes, the code is standard Next.js App Router code, allowing you to add route handlers (`/api/*`), connect Prisma, Drizzle, Supabase, or any REST/GraphQL endpoints seamlessly.",
    },
  ],
  contactText = "Still have questions? Reach out to our engineering team",
  contactHref = "#contact",
  className,
}: FaqAccordionProps) {
  return (
    <section
      id="faq"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto space-y-3 mb-10">
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

        {/* Collapsible Accordion Box */}
        <div className="bg-card rounded-2xl border border-border p-4 sm:p-8 shadow-sm">
          <Accordion type="single" collapsible className="w-full">
            {items.map((item, idx) => (
              <AccordionItem key={idx} value={`item-${idx}`} className="border-border">
                <AccordionTrigger className="text-left font-semibold text-sm sm:text-base text-foreground hover:no-underline hover:text-primary py-4">
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        {/* Contact Footer Help */}
        {contactText && (
          <div className="mt-8 text-center flex flex-col sm:flex-row items-center justify-center gap-2 text-sm text-muted-foreground">
            <HelpCircle className="h-4 w-4 text-primary" />
            <span>{contactText}</span>
            <Button variant="link" size="sm" asChild className="p-0 h-auto font-semibold">
              <a href={contactHref}>Contact Support &rarr;</a>
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}
