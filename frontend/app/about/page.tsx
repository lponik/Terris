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
    title: "AI Usage",
    summary: "AI (Gemini) is used to explain the results in clear, structured language.",
    details: [
      "The score itself is always computed deterministically by the backend.",
      "If AI is unavailable, the core analysis still works exactly the same.",
      "AI adds explanation - not authority.",
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

        <section className="space-y-5">
          {aboutSections.map((section, index) => (
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

              <div className="mt-0 max-h-0 overflow-hidden opacity-0 transition-[max-height,opacity,margin,transform] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] -translate-y-1 group-hover:mt-4 group-hover:max-h-[700px] group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:mt-4 group-focus-within:max-h-[700px] group-focus-within:translate-y-0 group-focus-within:opacity-100">
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
                {section.caution ? (
                  <p className="mt-3 rounded-lg border border-border bg-panel/65 px-3.5 py-2.5 text-sm text-center text-muted md:text-base">
                    {section.caution}
                  </p>
                ) : null}
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
