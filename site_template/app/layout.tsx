import type { Metadata } from "next"
import "./globals.css"

// Default layout of the site template; the frontend compiler (D-226) writes each site's own layout.
export const metadata: Metadata = { title: "FORGE site", description: "A website built by FORGE" }

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  )
}
