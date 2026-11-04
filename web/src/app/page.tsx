import { ApiStatusProvider } from "@/components/api-status-provider";
import { DemoSection } from "@/components/landing/demo-section";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Infrastructure } from "@/components/landing/infrastructure";
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
      <ApiStatusProvider>
        <main className="flex-1">
          <Hero />
          <HowItWorks />
          <DemoSection />
          <ResultsSection />
          <Infrastructure />
        </main>
      </ApiStatusProvider>
      <SiteFooter />
    </>
  );
}
