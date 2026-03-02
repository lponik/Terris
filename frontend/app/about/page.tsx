import ScrollReveal from "@/components/ScrollReveal";

const aboutSections = [
  {
    title: "Data Sources",
    summary: "Terris aggregates publicly available federal datasets, including:",
    details: [
      "Landfill site records",
      "Military base locations",
      "Industrial facility registry points",
      "EPA Superfund (NPL) sites",
    ],
    caution:
      "These sources provide location-based records of regulated or historically significant environmental sites.",
  },
  {
    title: "How It Works",
    summary: "Terris uses a consistent, rules-based approach:",
    details: [
      "It calculates how close your selected point is to different types of environmental sites.",
      "It counts how many regulated facilities are within set distance ranges.",
      "These signals are combined into a 0-10 Environmental Exposure Proxy Score.",
      "A transparent evidence list shows exactly which nearby records contributed to the result.",
      "The scoring system is deterministic - meaning the same location always produces the same result, based strictly on the data.",
    ],
    caution: "",
  },
  {
    title: "Limitations and What's Next",
    summary: "Terris is a screening tool, not a contamination test.",
    details: [
      "It does not measure water, soil, or air.",
      "It depends on the completeness and recency of public datasets.",
      "Proximity and category presence provide context - not proof of exposure.",
      "Next steps include:",
      "Improving category filtering and data quality signals",
      "Adding richer transparency around dataset coverage",
      "Expanding educational and policy context",
    ],
    caution: "",
  },
];

export default function AboutPage() {
  return (
    <main className="w-full px-4 py-8 md:px-5 md:py-10">
      <div className="mx-auto max-w-[1100px] space-y-5">
        <header className="rounded-2xl border border-border bg-panel/60 p-7 text-center md:p-8">
          <p className="text-sm font-medium text-muted">About Terris</p>
          <h1 className="mt-2 text-4xl font-bold leading-tight text-ink md:text-5xl">
            Built For Transparent Environmental Awareness
          </h1>
          <p className="mt-4 text-base text-muted md:text-lg">
            Terris exists to make environmental context easier to understand.
          </p>
          <p className="mt-3 text-base text-muted md:text-lg">
            Environmental data is public - but it's often scattered, technical, and difficult to interpret. Terris
            brings federal site data into one place and translates it into something simple, consistent, and
            inspectable.
          </p>
          <p className="mt-3 text-base text-muted md:text-lg">
            The goal is not to diagnose contamination. The goal is to help people explore, ask better questions, and
            understand what's around them.
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
