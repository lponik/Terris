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
            Remember to use cautious language: results may be associated with exposure context and do not, by themselves, confirm
            contamination or health outcomes. Hover over each of the boxes to learn more!
          </p>
        </header>

        <section className="space-y-5">
          {sections.map((section, index) => (
            <article
              key={section.title}
              tabIndex={0}
              className="group animate-revealUp rounded-2xl border border-border bg-panel/52 p-6 text-center transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1 hover:border-accent/45 hover:bg-panel/70 hover:shadow-[0_0_0_1px_rgba(15,111,67,0.34),0_22px_54px_rgba(15,111,67,0.24)] focus:outline-none focus-visible:-translate-y-1 focus-visible:border-accent/45 focus-visible:bg-panel/70 focus-visible:shadow-[0_0_0_1px_rgba(15,111,67,0.34),0_22px_54px_rgba(15,111,67,0.24)]"
              style={{ animationDelay: `${80 + index * 55}ms` }}
            >
              <div className="flex items-start justify-center gap-4">
                <h2 className="text-lg font-semibold text-ink md:text-xl">{section.title}</h2>

              </div>

              <p className="mt-3 text-base leading-relaxed text-muted md:text-lg">{section.summary}</p>
              <div className="mt-0 max-h-0 overflow-hidden opacity-0 transition-[max-height,opacity,margin,transform] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] -translate-y-1 group-hover:mt-4 group-hover:max-h-[640px] group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:mt-4 group-focus-within:max-h-[640px] group-focus-within:translate-y-0 group-focus-within:opacity-100">
                <p className="mt-1 rounded-lg border border-accent/25 bg-accent/8 px-3.5 py-2.5 text-sm text-ink md:text-base">
                  <span className="font-semibold">In plain language:</span> {section.plain}
                </p>
                <ul className="space-y-2.5">
                  {section.details.map((detail) => (
                    <li
                      key={detail}
                      className="rounded-lg bg-panelSoft/55 px-3.5 py-2.5 text-base text-center text-ink md:text-lg"
                    >
                      {detail}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 rounded-lg border border-border bg-panel/65 px-3.5 py-2.5 text-sm text-center text-muted md:text-base">
                  {section.caution}
                </p>
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
