export function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold">About the Metalcore Index</h1>
        <p className="text-gray-400 mt-2">
          AI-powered industry intelligence for heavy music.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-gray-200">What is this?</h2>
        <p className="text-gray-400 leading-relaxed">
          The Metalcore Index tracks momentum, industry positioning, and
          engagement metrics across the heavy music ecosystem. It combines
          Spotify popularity data, YouTube engagement, label/producer
          relationships, and release timing into a composite score that
          surfaces which artists are ascending, stable, or at risk.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-gray-200">Scoring Model</h2>
        <div className="bg-surface-raised border border-surface-border rounded-xl p-5 space-y-4">
          <ScoreSection
            title="Trajectory (40%)"
            description="Spotify popularity delta, follower growth rate, YouTube view acceleration. Measures momentum direction and velocity."
          />
          <ScoreSection
            title="Industry Signal (30%)"
            description="Label tier, producer tier, booking agency tier, management tier. Based on tier classifications from industry research."
          />
          <ScoreSection
            title="Engagement (20%)"
            description="Track popularity distribution depth (not just one hit), YouTube comment velocity relative to views."
          />
          <ScoreSection
            title="Release Positioning (10%)"
            description="Months since last release mapped to release cycle phase. Peak activity scores highest."
          />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-gray-200">Grades</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <GradeCard grade="A" range="80-100" label="Elite momentum" />
          <GradeCard grade="B" range="60-79" label="Strong position" />
          <GradeCard grade="C" range="40-59" label="Mid-tier / developing" />
          <GradeCard grade="D" range="0-39" label="Low signal / unsigned" />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-gray-200">Limitations</h2>
        <ul className="text-gray-400 space-y-1.5 text-sm list-disc list-inside">
          <li>
            Spotify monthly listeners are not available via API; popularity
            score (0-100) is used as a proxy.
          </li>
          <li>
            YouTube data requires manually seeded channel IDs (Search API too
            expensive).
          </li>
          <li>
            Social media metrics (Instagram, TikTok) are not included in MVP.
          </li>
          <li>
            Predictive signals require 90+ days of historical data to calibrate.
          </li>
          <li>
            Industry signal relies on static tier classifications from research
            report data, not real-time deal tracking.
          </li>
        </ul>
      </section>

      <section className="space-y-3 pb-8">
        <h2 className="text-xl font-semibold text-gray-200">Credits</h2>
        <p className="text-gray-400 text-sm">
          Built by Matthew Scott. Data sourced from Spotify API, YouTube Data
          API, MusicBrainz, and original industry research. Scoring methodology
          developed through analysis of the heavy music landscape documented in
          a 1,000+ line intelligence report.
        </p>
      </section>
    </div>
  );
}

function ScoreSection({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
      <p className="text-sm text-gray-500 mt-0.5">{description}</p>
    </div>
  );
}

function GradeCard({
  grade,
  range,
  label,
}: {
  grade: string;
  range: string;
  label: string;
}) {
  const cls = `grade-${grade.toLowerCase()}`;
  return (
    <div
      className={`${cls} rounded-lg p-3 text-center`}
    >
      <div className="text-2xl font-bold">{grade}</div>
      <div className="text-xs mt-1 opacity-80">{range}</div>
      <div className="text-xs mt-0.5 opacity-60">{label}</div>
    </div>
  );
}
