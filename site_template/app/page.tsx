import { Navbar } from "@/components/Navbar"
import { Hero } from "@/components/Hero"
import { ServicesPriceList } from "@/components/ServicesPriceList"
import { FaqAccordion } from "@/components/FaqAccordion"
import { ContactForm } from "@/components/ContactForm"
import { Footer } from "@/components/Footer"

// Sample page of the site template, used to check the template builds (Phase 3 Group 1). Every generated site
// replaces it with its own pages written by the frontend compiler (D-226), props as JSON literals like these.
export default function Home() {
  return (
    <>
      <Navbar {...{ "brandName": "Sample Bakery" }} />
      <Hero {...{ "headline": "Fresh cakes, baked every morning", "subheadline": "Order a custom cake for any day.",
                  "primaryCtaText": "Order a cake", "primaryCtaHref": "#contact", "variant": "editorial" }} />
      <ServicesPriceList />
      <FaqAccordion />
      <ContactForm />
      <Footer />
    </>
  )
}
