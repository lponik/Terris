import ScrollReveal from "@/components/ScrollReveal";

const sections = [
  {
    title: "What This Score Means",
    plain:
      "It's like a 'nearby activity' meter. It looks at what's around your point (within a few miles) and summarizes that into a single number.",
    summary:
      "This score is a quick, consistent way to understand what kinds of environmental sites are nearby. It helps you decide where to look closer.",
    details: [
      "This tool does not test your water, soil, or air. It only uses location-based data.",
      "A higher score usually means more sites nearby, or a very close site, based on the map's distance rules.",
      "Use it as a starting point: 'Should I dig deeper here?' not 'Is this place safe/unsafe?'",
    ],
    caution:
      "A high score does not prove contamination, and a low score does not guarantee there isn't an issue. It's a guide for where to ask better questions.",
  },
  {
    title: "Superfund (NPL) Sites",
    plain:
      "Superfund sites are places the EPA has identified as needing long-term cleanup work because of past contamination.",
    summary:
      "Seeing a Superfund site nearby can be an important clue about local history. It doesn't automatically mean your exact spot is affected.",
    details: [
      "Different Superfund sites are in different stages (investigation, cleanup, monitoring, etc.).",
      "Some sites have controls in place (like caps or restricted areas) that reduce risk pathways.",
      "Distance alone can't tell you whether anything reaches your address; local reports matter.",
    ],
    caution:
      "Nearby Superfund = 'worth learning more,' not 'proof of exposure.' Always check official site pages or local agency updates.",
  },
  {
    title: "PFAS and Military Bases",
    plain:
      "PFAS are long-lasting chemicals that were used in some firefighting foams (often called AFFF), including at some military and airport locations.",
    summary:
      "Military proximity is included because some bases have historical PFAS-related investigations. But this varies a lot by location and time period.",
    details: [
      "Not every base has the same history; some have documented PFAS studies, others do not.",
      "The most useful next step is to look up base-specific reports or state agency pages.",
      "This map signal is about 'possible relevance,' not a confirmation of PFAS in your area.",
    ],
    caution:
      "Being near a military base does not automatically mean PFAS contamination. Treat it as a prompt to check official sources.",
  },
  {
    title: "Landfills",
    plain:
      "Landfills are places where waste is stored. Older vs. newer landfills can be very different, depending on liners, monitoring, and cleanup status.",
    summary:
      "Landfills are included because waste infrastructure can be part of a broader environmental picture. Proximity is just a first clue.",
    details: [
      "Modern landfills often have engineering controls (liners, leachate systems, monitoring).",
      "Older or closed sites may have different records and oversight than modern sites.",
      "The best follow-up is local landfill permit/monitoring information from state or county sources.",
    ],
    caution:
      "A nearby landfill does not prove contamination at your location. It suggests a reason to look at local records.",
  },
  {
    title: "Industrial Facility Density",
    plain:
      "This counts how many regulated facilities are nearby within 1, 3, and 10 miles. Think of it as a 'how busy is this area' signal.",
    summary:
      "Industrial density is used as a proxy for nearby industrial activity. It's about concentration, not the danger level of any single facility.",
    details: [
      "Different facilities can be very different: size, chemicals, permits, controls, and reporting requirements vary.",
      "Counts help you compare areas (quiet rural vs. dense industrial corridor), but they don't measure exposure.",
      "Use the evidence list to see what's nearby, then look those sites up in official records.",
    ],
    caution:
      "More facilities nearby can mean more context to review, but it does not automatically translate to a specific health risk.",
  },
  {
    title: "Limitations and Responsible Use",
    plain:
      "This tool helps you ask better questions. For real answers, you'll still want official reports and local testing when appropriate.",
    summary:
      "This is a map-based screening tool. It's useful for awareness and prioritization, but it can't capture every local factor.",
    details: [
      "Data can be incomplete or out of date depending on the source and area.",
      "The score uses fixed distance bands, which is simple and consistent, but not perfect for every situation.",
      "Local conditions matter (wind, groundwater, site controls, time period). Those aren't fully captured here.",
    ],
    caution:
      "Use this for transparency and prioritization, not as a diagnosis, legal proof, or a final safety determination.",
  },
];

export default function LearnPage() {
  return (
    <main className="w-full px-4 py-8 md:px-5 md:py-10">
      <div className="mx-auto max-w-[1100px] space-y-5">
        <header className="rounded-2xl border border-border bg-panel/60 p-7 text-center md:p-8">
          <p className="text-sm font-medium text-muted">Learn</p>
          <h1 className="mt-2 text-4xl font-bold leading-tight text-ink md:text-5xl">
            How To Interpret This Map
          </h1>
          <p className="mt-4 text-base text-muted md:text-lg">
            Remember to use cautious language: results may be associated with exposure context and do not, by
            themselves, confirm contamination or health outcomes. Scroll down and each card will reveal as it enters
            view.
          </p>
        </header>

        <section className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {sections.map((section, index) => (
            <ScrollReveal key={section.title} className="h-full" delayMs={index * 75}>
              <article
                tabIndex={0}
                className="group flex h-full flex-col rounded-2xl border border-border bg-panel/58 p-5 text-left transform-gpu will-change-transform transition-[transform,box-shadow,border-color,background-color] duration-[520ms] ease-[cubic-bezier(0.22,1,0.36,1)] hover:z-10 hover:-translate-y-1.5 hover:scale-[1.035] hover:border-accent/45 hover:bg-panel/74 hover:shadow-[0_0_0_1px_rgba(15,111,67,0.32),0_24px_56px_rgba(7,19,12,0.36)] focus:outline-none focus-visible:z-10 focus-visible:-translate-y-1.5 focus-visible:scale-[1.035] focus-visible:border-accent/45 focus-visible:bg-panel/74 focus-visible:shadow-[0_0_0_1px_rgba(15,111,67,0.32),0_24px_56px_rgba(7,19,12,0.36)] motion-reduce:transform-none motion-reduce:transition-none md:min-h-[350px] md:p-6"
              >
                <h2 className="text-3xl font-semibold leading-tight text-ink">{section.title}</h2>
                <p className="mt-3 rounded-lg border border-accent/30 bg-accent/8 px-3 py-2 text-base leading-relaxed text-ink/95 md:text-[1.05rem]">
                  <span className="font-semibold">In plain language:</span> {section.plain}
                </p>
                <p className="mt-3 text-base leading-relaxed text-muted md:text-lg">{section.summary}</p>

                <ul className="mt-4 space-y-2.5">
                  {section.details.map((detail) => (
                    <li
                      key={detail}
                      className="rounded-lg bg-panelSoft/56 px-3 py-2 text-base leading-relaxed text-ink/95 md:text-[1.03rem]"
                    >
                      {detail}
                    </li>
                  ))}
                </ul>

                <p className="mt-4 rounded-lg border border-border bg-panel/70 px-3 py-2 text-base leading-relaxed text-muted md:text-[1.03rem]">
                  {section.caution}
                </p>
              </article>
            </ScrollReveal>
          ))}
        </section>
      </div>
    </main>
  );
}
