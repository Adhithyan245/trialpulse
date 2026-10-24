import { Hero } from "./landing/Hero";
import { ProofStrip } from "./landing/ProofStrip";
import { HowItWorks } from "./landing/HowItWorks";
import { Footer } from "./landing/Footer";

export function Landing() {
  return (
    <div className="mx-auto max-w-5xl">
      <Hero />
      <ProofStrip />
      <HowItWorks />
      <Footer />
    </div>
  );
}
