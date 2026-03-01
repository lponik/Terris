import Link from "next/link";
import StarfieldBackground from "@/components/StarfieldBackground";

export default function HomePage() {
  return (
    <main className="relative isolate flex min-h-[calc(100vh-3.5rem)] items-center justify-center overflow-hidden px-6">
      <StarfieldBackground />
      <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(circle_at_center,rgba(10,24,17,0.2)_0%,rgba(2,5,3,0.92)_80%)]" />

      <section className="terris-hero relative z-10 mx-auto max-w-3xl text-center">
        <h1 className="terris-logo terris-wordmark text-7xl font-bold leading-none tracking-[-0.03em] text-ink sm:text-8xl md:text-9xl">
          Terris
        </h1>
        <p className="terris-subtitle mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-muted sm:text-base md:text-lg">      
          Explore proximity to superfund sites, landfills, military bases, and regulated facilities in the US.
        </p>
        <Link
          href="/map"
          className="terris-cta mt-8 inline-flex items-center justify-center rounded-md border border-accent/60 bg-accent/18 px-8 py-4 text-base font-semibold uppercase tracking-[0.14em] text-ink transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas"
        >
          Try now
        </Link>
      </section>
    </main>
  );
}
