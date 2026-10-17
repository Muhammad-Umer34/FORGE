// Professional credentials section displaying text-labelled skill proficiencies, work experience history, and educational background

"use client"

import React from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Briefcase, GraduationCap, Award, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SkillItem {
  name: string
  level: string // e.g. "Expert", "Advanced", "Proficient" (required text label for accessibility)
  percentage?: number // 0-100 for visual bar
  category?: string
}

export interface ExperienceItem {
  role: string
  company: string
  period: string
  description: string
  highlights?: string[]
}

export interface EducationItem {
  degree: string
  institution: string
  year: string
  honors?: string
}

export interface ResumeSkillsProps {
  badgeText?: string
  title?: string
  subtitle?: string
  skills?: SkillItem[]
  experience?: ExperienceItem[]
  education?: EducationItem[]
  className?: string
}

export function ResumeSkills({
  badgeText = "Credentials & Experience",
  title = "Skills & Professional Background",
  subtitle = "A summary of technical proficiencies, professional track record, and educational credentials.",
  skills = [
    { name: "Full-Stack Development", level: "Expert", percentage: 95 },
    { name: "System Architecture", level: "Advanced", percentage: 85 },
    { name: "UI/UX & Design Systems", level: "Advanced", percentage: 80 },
    { name: "Database Engineering", level: "Proficient", percentage: 75 },
    { name: "Cloud & DevOps Operations", level: "Proficient", percentage: 70 },
  ],
  experience = [
    {
      role: "Lead Systems Architect",
      company: "Modern Tech Studio",
      period: "2024 – Present",
      description: "Spearheaded core platform engineering, accelerating client deployment cycles and mentoring junior developers.",
      highlights: ["Engineered reusable UI component architecture", "Reduced build latencies by 40%"],
    },
    {
      role: "Senior Full Stack Engineer",
      company: "Digital Solutions Group",
      period: "2021 – 2024",
      description: "Designed responsive web interfaces and resilient API microservices across varied client industries.",
    },
  ],
  education = [
    {
      degree: "B.S. in Computer Science",
      institution: "State University of Technology",
      year: "2021",
      honors: "Summa Cum Laude",
    },
  ],
  className,
}: ResumeSkillsProps) {
  return (
    <section id="resume-skills" className={cn("w-full py-16 sm:py-24 bg-background border-b border-border/40", className)}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-3xl mx-auto text-center space-y-3 mb-16">
          {badgeText && (
            <Badge variant="outline" className="text-primary border-primary/30">
              {badgeText}
            </Badge>
          )}
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">{title}</h2>
          {subtitle && <p className="text-base text-muted-foreground">{subtitle}</p>}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          {/* Left Column: Skills Bars (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="flex items-center gap-2 font-bold text-lg text-foreground pb-2 border-b border-border">
              <Award className="h-5 w-5 text-primary" />
              <h3>Core Proficiencies</h3>
            </div>

            <div className="space-y-5">
              {skills?.map((skill, idx) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-foreground">{skill.name}</span>
                    {/* Explicit Accessible Text Label for Proficiency Level */}
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20">
                      {skill.level}
                    </span>
                  </div>
                  {/* Progress Indicator */}
                  {skill.percentage !== undefined && (
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(0, skill.percentage))}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Right Column: Experience & Education (7 cols) */}
          <div className="lg:col-span-7 space-y-10">
            {/* Work Experience */}
            <div className="space-y-6">
              <div className="flex items-center gap-2 font-bold text-lg text-foreground pb-2 border-b border-border">
                <Briefcase className="h-5 w-5 text-primary" />
                <h3>Experience History</h3>
              </div>

              <div className="space-y-4">
                {experience?.map((exp, idx) => (
                  <Card key={idx} className="border-border bg-card p-5 shadow-xs">
                    <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
                      <h4 className="font-bold text-base text-foreground">{exp.role}</h4>
                      <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {exp.period}
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-primary mb-2">{exp.company}</div>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed mb-3">
                      {exp.description}
                    </p>
                    {exp.highlights && exp.highlights.length > 0 && (
                      <ul className="space-y-1 pt-2 border-t border-border/40 text-xs text-muted-foreground">
                        {exp.highlights.map((h, hIdx) => (
                          <li key={hIdx} className="flex items-start gap-1.5">
                            <CheckCircle2 className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
                            <span>{h}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                ))}
              </div>
            </div>

            {/* Education */}
            {education && education.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 font-bold text-lg text-foreground pb-2 border-b border-border">
                  <GraduationCap className="h-5 w-5 text-primary" />
                  <h3>Education</h3>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {education.map((edu, idx) => (
                    <Card key={idx} className="border-border bg-card p-5">
                      <span className="text-xs text-muted-foreground">{edu.year}</span>
                      <h4 className="font-bold text-sm text-foreground mt-0.5">{edu.degree}</h4>
                      <div className="text-xs text-muted-foreground mt-1">{edu.institution}</div>
                      {edu.honors && (
                        <div className="text-[11px] font-semibold text-primary mt-2">{edu.honors}</div>
                      )}
                    </Card>
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
