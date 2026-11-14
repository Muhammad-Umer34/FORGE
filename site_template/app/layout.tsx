import type { Metadata } from "next"
import "./globals.css"

// Default layout of the site template; the frontend compiler (D-226) writes each site's own layout.
export const metadata: Metadata = { title: "FORGE site", description: "A website built by FORGE" }

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      {/* the design direction (D-224, app/direction.css); the compiler writes each site's own choices */}
      <body className="min-h-screen antialiased" data-density="balanced" data-corners="soft" data-type="calm"
            data-surfaces="cards" data-rhythm="continuous" data-images="rounded" data-headings="eyebrow">
        <main>{children}</main>
      </body>
    </html>
  )
}
