import ScrollReveal from "@/components/ScrollReveal";

const aboutSections = [
  {
    title: "Data Sources",
    summary: "Terris combines three public federal datasets:",
    details: [
      "EPA Superfund National Priorities List site boundaries",
      "U.S. DOT Bureau of Transportation Statistics military base records",
      "EPA Landfill Methane Outreach Program landfill records",
    ],
    caution: "Processed records are normalized into one inspectable location dataset.",
  },
  {
    title: "How It Works",
    summary: "Choose a point and Terris runs the same fixed calculation every time:",
    details: [
      "Measure great-circle distance to the nearest site in each category",
      "Apply published proximity thresholds to produce a 0–10 screening score",
      "Show the nearest source records behind the result",
    ],
    caution: "The method is deterministic: the same point and dataset produce the same result.",
  },
  {
    title: "Limitations",
    summary: "Terris provides context, not a finding of contamination or exposure.",
    details: [
      "Representative points do not describe a site's full footprint",
      "Public records may be incomplete, delayed, or imprecise",
      "Distance does not measure contaminants in air, water, or soil",
    ],
    caution: "Use official site records and local testing for decisions about a specific property.",
  },
];

export default function AboutPage() {
  return (
    <main className="w-full px-4 py-8 md:px-5 md:py-10">
      <div className="mx-auto max-w-[1100px] space-y-5">
        <header className="rounded-2xl border border-border bg-panel/60 p-7 text-center md:p-8">
          <p className="text-sm font-medium text-muted">About Terris</p>
          <h1 className="mt-2 text-4xl font-bold leading-tight text-ink md:text-5xl">
            Environmental context, made inspectable
          </h1>
          <p className="mx-auto mt-4 max-w-3xl text-base text-muted md:text-lg">
            Terris turns three public site datasets into a transparent proximity screening tool. It helps people see
            what is nearby and inspect the records behind the score.
          </p>
        </header>

        <section className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {aboutSections.map((section, index) => (
            <ScrollReveal key={section.title} className="h-full" delayMs={index * 70}>
              <article
                tabIndex={0}
                className="group flex h-full flex-col rounded-2xl border border-border bg-panel/58 p-5 text-left transform-gpu will-change-transform transition-[transform,box-shadow,border-color,background-color] duration-[520ms] ease-[cubic-bezier(0.22,1,0.36,1)] hover:z-10 hover:-translate-y-1.5 hover:scale-[1.035] hover:border-accent/45 hover:bg-panel/74 hover:shadow-[0_0_0_1px_rgba(15,111,67,0.32),0_24px_56px_rgba(7,19,12,0.36)] focus:outline-none focus-visible:z-10 focus-visible:-translate-y-1.5 focus-visible:scale-[1.035] focus-visible:border-accent/45 focus-visible:bg-panel/74 focus-visible:shadow-[0_0_0_1px_rgba(15,111,67,0.32),0_24px_56px_rgba(7,19,12,0.36)] motion-reduce:transform-none motion-reduce:transition-none md:min-h-[320px] md:p-6"
              >
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted/95">{`0${index + 1}`}</p>
                <h2 className="mt-2 text-2xl font-semibold leading-tight text-ink">{section.title}</h2>
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

                {section.caution ? (
                  <p className="mt-4 rounded-lg border border-border bg-panel/70 px-3 py-2 text-base leading-relaxed text-muted md:text-[1.03rem]">
                    {section.caution}
                  </p>
                ) : null}
              </article>
            </ScrollReveal>
          ))}
        </section>
      </div>
    </main>
  );
}
