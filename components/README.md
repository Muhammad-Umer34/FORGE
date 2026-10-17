# FORGE Component & Section Library

A production-ready component library of 49 reusable React & Next.js sections and site-wide utilities built for autonomous AI generation of small-business websites (bakeries, clinics, consultants, portfolios, retail shops).

---

## Architecture & Conventions

- **Zero External Dependencies**: Built entirely on standard React 19, Next.js 16, `@radix-ui/*`, `clsx`, `tailwind-merge`, and `lucide-react`.
- **Mobile-First Responsiveness**: Every component is designed to render seamlessly from 320 px to 1440 px+ displays.
- **Theme Variables**: Relies strictly on semantic Tailwind theme variables (`bg-background`, `text-foreground`, `border-border`, `text-primary`, etc.). No hardcoded hex values.
- **Defensive Prop Fallbacks**: Every prop defines a generic, business-neutral default fallback. Missing optional props or empty lists render clean states without breaking page layouts.
- **Client & Server Safe**: Interactive components declare `"use client"`. Server metadata helpers export standard Next.js `Metadata` types.

---

## Catalogue & Schema Specifications

The component catalog is maintained in [`components_catalog.json`](./components_catalog.json) and synced to `server/data/components_catalog.json`.

Every section entry follows this schema:
```json
{
  "component_id": "business-hours",
  "name": "Business Hours & Schedule",
  "category": "Contact",
  "feature": "Business hours",
  "contentNeeds": ["hours"],
  "dataNeeds": [],
  "description": "Business hours, opening times, weekly operating schedule, and open now status indicator..."
}
```

- **`feature`**: Plain-language feature title.
- **`contentNeeds`**: Business details required from the site owner (`business_name`, `phone`, `whatsapp`, `email`, `address`, `map_embed_url`, `hours`, `social_handles`, `logo`, `photos`, `items`, `prices`, `about_text`, `video_url`).
- **`dataNeeds`**: Dynamic database entities read or written (`order_requests`, `subscribers`, `blog_posts`, `events`, `availability`, or `[]`).
- **`description`**: Natural-language description optimized for semantic vector retrieval.

---

## Site-Wide Utilities & Non-Section Components (Batch 3)

### 1. `SeoHead` & `constructMetadata()`
- **File**: [`SeoHead.tsx`](./SeoHead.tsx)
- **Purpose**: Dual-mode SEO manager supporting Next.js 16 App Router metadata generation and client-side page title/meta synchronization.
- **Usage (Server Component / Layout)**:
  ```tsx
  import { constructMetadata } from "@/components/library"
  export const metadata = constructMetadata({
    title: "About Our Bakery",
    description: "Handcrafted artisan sourdough and pastries.",
    canonicalUrl: "https://example.com/about",
  })
  ```
- **Usage (Client Component)**:
  ```tsx
  import { SeoHead } from "@/components/library"
  <SeoHead title="Custom Cakes" description="Pre-order customized wedding cakes." />
  ```

### 2. `NotFoundPage`
- **File**: [`NotFoundPage.tsx`](./NotFoundPage.tsx)
- **Purpose**: Accessible, friendly 404 page layout with home navigation and support links.
- **Props**: `title`, `subtitle`, `homeLabel`, `homeHref`, `supportLabel`, `supportHref`.

### 3. Shared Loading & Error States
- **File**: [`LoadingAndErrorStates.tsx`](./LoadingAndErrorStates.tsx)
- **Components**:
  - `<ComponentSkeleton type="card-grid" | "form" | "table" | "list" | "hero" count={3} />`: Universal animated pulse loading state matching shadcn conventions.
  - `<ComponentErrorState title="..." message="..." onRetry={...} />`: User-friendly error card with retry callback.

---

## Vector Embeddings Regeneration

To synchronize semantic vector retrieval when catalog entries or descriptions are updated:

```bash
python scripts/generate_component_embeddings.py
```

This reads [`components/components_catalog.json`](./components_catalog.json) and outputs 384-dimensional normalized vectors to [`components/component_embeddings.json`](./component_embeddings.json) using `sentence-transformers` (`all-MiniLM-L6-v2`).
