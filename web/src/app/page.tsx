import { Architecture } from "@/components/landing/architecture";
import { DemoSection } from "@/components/landing/demo-section";
import { Hero } from "@/components/landing/hero";
import { Highlights } from "@/components/landing/highlights";
import { HowItWorks } from "@/components/landing/how-it-works";
import { ResultsSection } from "@/components/landing/results-section";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";

export default function Home() {
  return (
    <>
      <a
        href="#demonstracao"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2"
      >
        Ir para a demonstração
      </a>
      <SiteHeader />
      <main className="flex-1">
        <Hero />
        <Highlights />
        <HowItWorks />
        <DemoSection />
        <ResultsSection />
        <Architecture />
      </main>
      <SiteFooter />
    </>
  );
}
