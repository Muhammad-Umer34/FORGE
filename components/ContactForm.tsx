// Contact form with name, email, subject, message input fields, direct submission handling, and business contact information

"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Mail, Phone, MapPin, Send, CheckCircle2, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface ContactFormData {
  name: string
  email: string
  subject: string
  message: string
}

export interface ContactFormProps {
  badgeText?: string
  title?: string
  subtitle?: string
  email?: string
  phone?: string
  address?: string
  submitButtonText?: string
  onSubmit?: (data: ContactFormData) => Promise<void> | void
  successMessage?: string
  className?: string
}

export function ContactForm({
  badgeText = "Get In Touch",
  title = "Let's Start a Conversation",
  subtitle = "Have a question, feedback, or custom project requirement? Drop us a message and our team will get back to you within 24 hours.",
  email = "hello@forge-builder.dev",
  phone = "+1 (555) 234-5678",
  address = "100 Innovation Way, Suite 400, San Francisco, CA",
  submitButtonText = "Send Message",
  onSubmit,
  successMessage = "Thank you! Your message has been sent successfully. We'll be in touch soon.",
  className,
}: ContactFormProps) {
  const [formData, setFormData] = useState<ContactFormData>({
    name: "",
    email: "",
    subject: "",
    message: "",
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (!formData.name || !formData.email || !formData.message) {
      setErrorMessage("Please fill in all required fields (Name, Email, Message).")
      return
    }

    try {
      setIsSubmitting(true)
      if (onSubmit) {
        await onSubmit(formData)
      } else {
        // Fallback simulate submission
        await new Promise((resolve) => setTimeout(resolve, 800))
      }
      setIsSubmitted(true)
      setFormData({ name: "", email: "", subject: "", message: "" })
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to send message. Please try again."
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section
      id="contact"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          {/* Left Column: Contact Details & Context */}
          <div className="lg:col-span-5 space-y-6">
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

            {/* Direct Info List */}
            <div className="space-y-4 pt-4 border-t border-border/60">
              {email && (
                <div className="flex items-center gap-3 text-sm text-foreground">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <Mail className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Email us directly</div>
                    <a href={`mailto:${email}`} className="font-medium hover:underline">
                      {email}
                    </a>
                  </div>
                </div>
              )}

              {phone && (
                <div className="flex items-center gap-3 text-sm text-foreground">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <Phone className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Call us</div>
                    <a href={`tel:${phone}`} className="font-medium hover:underline">
                      {phone}
                    </a>
                  </div>
                </div>
              )}

              {address && (
                <div className="flex items-center gap-3 text-sm text-foreground">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Headquarters</div>
                    <span className="font-medium">{address}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Contact Form Card */}
          <div className="lg:col-span-7">
            <Card className="border-border shadow-md">
              <CardHeader>
                <CardTitle className="text-xl">Send us a Message</CardTitle>
                <CardDescription>
                  Fill out the form below and we will get back to you promptly.
                </CardDescription>
              </CardHeader>

              <CardContent>
                {isSubmitted ? (
                  <div className="p-6 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center space-y-3">
                    <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
                    <h4 className="font-semibold text-foreground">Message Sent!</h4>
                    <p className="text-sm text-muted-foreground">{successMessage}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsSubmitted(false)}
                      className="mt-2"
                    >
                      Send Another Message
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    {errorMessage && (
                      <div className="p-3 rounded-md bg-destructive/10 text-destructive text-xs">
                        {errorMessage}
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">
                          Full Name <span className="text-destructive">*</span>
                        </Label>
                        <Input
                          id="name"
                          placeholder="Jane Doe"
                          value={formData.name}
                          onChange={(e) =>
                            setFormData({ ...formData, name: e.target.value })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="email">
                          Email Address <span className="text-destructive">*</span>
                        </Label>
                        <Input
                          id="email"
                          type="email"
                          placeholder="jane@example.com"
                          value={formData.email}
                          onChange={(e) =>
                            setFormData({ ...formData, email: e.target.value })
                          }
                          required
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="subject">Subject</Label>
                      <Input
                        id="subject"
                        placeholder="Inquiry about custom web project..."
                        value={formData.subject}
                        onChange={(e) =>
                          setFormData({ ...formData, subject: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="message">
                        Your Message <span className="text-destructive">*</span>
                      </Label>
                      <Textarea
                        id="message"
                        rows={4}
                        placeholder="Tell us more about your ideas, timeline, and goals..."
                        value={formData.message}
                        onChange={(e) =>
                          setFormData({ ...formData, message: e.target.value })
                        }
                        required
                      />
                    </div>

                    <Button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full sm:w-auto gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <Send className="h-4 w-4" />
                          {submitButtonText}
                        </>
                      )}
                    </Button>
                  </form>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  )
}
