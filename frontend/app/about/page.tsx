import ScrollReveal from "@/components/ScrollReveal";

const GITHUB_URL = "https://github.com/lponik/Terris";

export default function AboutPage() {
  return (
    <main className="w-full px-4 py-8 md:px-5 md:py-10">
      <div className="mx-auto max-w-[1080px] space-y-5">
        <ScrollReveal>
          <header className="rounded-2xl border border-border bg-panel/60 p-7 md:p-10">
            <h1 className="max-w-3xl text-4xl font-bold leading-tight text-ink md:text-5xl">
              What is Terris?
            </h1>
            <div className="mt-5 max-w-4xl space-y-4 text-base leading-relaxed text-muted md:text-lg">
              <p>
                Terris is an environmental proximity map built to make public environmental data easier to explore.
              </p>
              <p>
                Information about Superfund sites and landfills are publicly available, but who wants to search through large government datasets and use unfamiliar tools.
              </p>
              <p>
                Terris brings that information into one place. 
              </p>
            </div>
          </header>
        </ScrollReveal>

        <ScrollReveal delayMs={70}>
          <section
            className="rounded-2xl border border-border bg-panel/58 p-6 md:p-8"
            aria-labelledby="site-types"
          >
            <h2 id="site-types" className="px-1 text-2xl font-semibold text-ink md:text-3xl">
              What are these sites?
            </h2>

            <div className="mt-5 grid overflow-hidden rounded-xl border border-border bg-panelSoft/35 md:grid-cols-2 md:divide-x md:divide-border">
              <article className="flex h-full flex-col p-5 md:p-6">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-hazardSuperfund">Superfund</p>
                <h3 className="mt-2 text-2xl font-semibold text-ink">Superfund Sites</h3>
                <div className="mt-3 flex-1 space-y-3 text-base leading-relaxed text-muted">
                  <p>
                    Superfund is an EPA program for sites where hazardous substances have been released, or could
                    potentially be released, into the environment.
                  </p>
                  <p>
                    Terris includes sites from the National Priorities List, along with additional mapped EPA Superfund
                    records and selected Superfund Alternative Approach locations with usable coordinates.
                  </p>
                </div>
                <p className="mt-6 font-mono text-2xl font-bold tabular-nums text-ink">1,924 mapped locations</p>
              </article>

              <article className="flex h-full flex-col border-t border-border p-5 md:border-t-0 md:p-6">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-hazardLandfill">Landfill</p>
                <h3 className="mt-2 text-2xl font-semibold text-ink">Landfills</h3>
                <div className="mt-3 flex-1 space-y-3 text-base leading-relaxed text-muted">
                  <p>Landfills are places where waste is disposed of and managed.</p>
                  <p>
                    Terris maps landfill locations from the EPA&apos;s Landfill Methane Outreach Program, which tracks
                    landfills and landfill-gas information across the United States.
                  </p>
                </div>
                <p className="mt-6 font-mono text-2xl font-bold tabular-nums text-ink">2,323 mapped locations</p>
              </article>
            </div>
          </section>
        </ScrollReveal>

        <ScrollReveal delayMs={190}>
          <section className="rounded-2xl border border-border bg-panel/58 p-6 md:p-8" aria-labelledby="data">
            <h2 id="data" className="text-2xl font-semibold text-ink md:text-3xl">Data</h2>
            <div className="mt-4 max-w-4xl space-y-3 text-base leading-relaxed text-muted md:text-lg">
              <p>
                Terris currently contains <strong className="text-ink">4,247 mapped locations</strong> from publicly
                available U.S. Environmental Protection Agency data.
              </p>
              <p>
                The source datasets are cleaned, standardized, and combined into a consistent format before being used
                by the map.
              </p>
            </div>
          </section>
        </ScrollReveal>

        <ScrollReveal delayMs={230}>
          <section className="rounded-2xl border border-border bg-panel/58 p-6 md:p-8" aria-labelledby="limitations">
            <h2 id="limitations" className="text-2xl font-semibold text-ink md:text-3xl">Limitations</h2>
            <p className="mt-4 text-lg font-bold text-warning">Terris measures proximity, not risk.</p>
            <div className="mt-3 max-w-4xl space-y-3 text-base leading-relaxed text-muted md:text-lg">
              <p>
                Being close to a mapped site does not necessarily mean you are exposed to contamination or that an area
                is unsafe.
              </p>
              <p>
                Terris does not estimate contaminant levels, personal exposure, health effects, or property safety. Site
                markers are based on coordinates from the underlying datasets and may not represent the exact location
                or full extent of contamination.
              </p>
              <p>
                For environmental or health decisions, refer to the original EPA records and appropriate professionals.
              </p>
            </div>
          </section>
        </ScrollReveal>

        <ScrollReveal delayMs={270}>
          <section className="rounded-2xl border border-border bg-panel/58 p-6 md:p-8" aria-labelledby="open-source">
            <h2 id="open-source" className="text-2xl font-semibold text-ink md:text-3xl">Open Source</h2>
            <p className="mt-4 max-w-4xl text-base leading-relaxed text-muted md:text-lg">
              Terris is an open-source project. The source code, data pipeline, methodology, and development history are
              available on GitHub.
            </p>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="mt-5 inline-flex rounded-lg border border-accent bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
            >
              View Terris on GitHub ↗
            </a>
          </section>
        </ScrollReveal>
      </div>
    </main>
  );
}
