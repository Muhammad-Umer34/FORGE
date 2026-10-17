// Team & Staff Grid: Profiles for doctors, attorneys, practitioners, instructors, and company founders

"use client"

import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Mail, Globe, Award, Stethoscope, GraduationCap } from "lucide-react"
import { cn } from "@/lib/utils"

export interface TeamMember {
  id?: string
  name: string
  role: string
  credentials?: string
  bio: string
  avatarUrl?: string
  specialties?: string[]
  email?: string
}

export interface TeamGridProps {
  badgeText?: string
  title?: string
  subtitle?: string
  members?: TeamMember[]
  className?: string
}

export function TeamGrid({
  badgeText = "Our Specialists",
  title = "Meet Our Dedicated Team of Experts",
  subtitle = "Our board-certified professionals combine decades of clinical experience with genuine care for every patient and client.",
  members = [
    {
      id: "m1",
      name: "Dr. Marcus Vance",
      role: "Lead Dental Surgeon & Founder",
      credentials: "DDS, FAGD",
      bio: "Over 16 years specializing in advanced restorative implants, cosmetic smile design, and painless laser dentistry.",
      avatarUrl: "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=400&q=80",
      specialties: ["Dental Implants", "Smile Design", "Laser Surgery"],
    },
    {
      id: "m2",
      name: "Dr. Alena Thorne",
      role: "Orthodontics & Pediatric Specialist",
      credentials: "MS, Orthodontics",
      bio: "Passionate about creating gentle, stress-free clinical experiences for children, teens, and adult alignment cases.",
      avatarUrl: "https://images.unsplash.com/photo-1594824813596-f94685934444?auto=format&fit=crop&w=400&q=80",
      specialties: ["Clear Aligners", "Pediatric Care", "Early Interception"],
    },
    {
      id: "m3",
      name: "James Henderson",
      role: "Senior Clinical Hygienist",
      credentials: "RDH, Periodontal Care",
      bio: "Dedicated to comprehensive preventive health, deep ultrasonic cleanings, and patient education on oral wellness.",
      avatarUrl: "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=400&q=80",
      specialties: ["Preventive Hygiene", "Stain Removal", "Periodontal Therapy"],
    },
  ],
  className,
}: TeamGridProps) {
  return (
    <section
      id="team"
      className={cn(
        "w-full py-16 sm:py-24 bg-background border-b border-border/40",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-12 sm:mb-16">
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

        {/* Members Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 items-stretch">
          {members.map((member, idx) => (
            <Card
              key={member.id || idx}
              className="overflow-hidden border-border bg-card/60 backdrop-blur shadow-sm hover:shadow-md transition-all duration-300 rounded-2xl flex flex-col justify-between group"
            >
              <div>
                {/* Photo Header */}
                <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted">
                  {member.avatarUrl ? (
                    <img
                      src={member.avatarUrl}
                      alt={member.name}
                      className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-primary/10 text-primary">
                      <Stethoscope className="h-16 w-16 stroke-1" />
                    </div>
                  )}
                  {member.credentials && (
                    <span className="absolute bottom-3 right-3 bg-zinc-950/80 backdrop-blur text-white text-[11px] font-semibold px-2.5 py-1 rounded-md border border-white/10 shadow-sm flex items-center gap-1">
                      <GraduationCap className="h-3.5 w-3.5 text-primary" />
                      {member.credentials}
                    </span>
                  )}
                </div>

                {/* Content */}
                <CardContent className="p-6 space-y-3">
                  <div>
                    <h3 className="font-semibold text-lg text-foreground group-hover:text-primary transition-colors">
                      {member.name}
                    </h3>
                    <p className="text-xs font-medium text-primary mt-0.5">
                      {member.role}
                    </p>
                  </div>

                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {member.bio}
                  </p>

                  {/* Specialties Tags */}
                  {member.specialties && member.specialties.length > 0 && (
                    <div className="pt-2 flex flex-wrap gap-1.5">
                      {member.specialties.map((spec, sIdx) => (
                        <span
                          key={sIdx}
                          className="text-[10px] font-medium bg-muted text-muted-foreground px-2 py-0.5 rounded-full border border-border/50"
                        >
                          {spec}
                        </span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </div>

              {/* Card Footer */}
              <div className="px-6 py-4 border-t border-border/50 bg-muted/20 flex items-center justify-between text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Award className="h-3.5 w-3.5 text-primary" />
                  Verified Specialist
                </span>
                <div className="flex items-center gap-2">
                  <button type="button" className="hover:text-primary transition-colors" title="Message">
                    <Mail className="h-4 w-4" />
                  </button>
                  <button type="button" className="hover:text-primary transition-colors" title="Website / Profile">
                    <Globe className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
