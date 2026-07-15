import Link from "next/link";

export default function Dashboard() {
  return (
    <main className="min-h-screen p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">TerraTrain</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          AI-powered terrain-aware endurance training coach
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <NavCard
          href="/coach"
          title="AI Coach"
          description="Generate terrain-aware workout plans"
          icon="🧠"
        />
        <NavCard
          href="/routes"
          title="Routes"
          description="Upload and analyze GPX tracks"
          icon="🗺️"
        />
        <NavCard
          href="/workouts"
          title="Workouts"
          description="Review and push workouts to Intervals.icu"
          icon="🚴"
        />
      </div>
    </main>
  );
}

function NavCard({
  href,
  title,
  description,
  icon,
}: {
  href: string;
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-gray-200 p-6 hover:border-gray-400 hover:shadow-sm transition-all dark:border-gray-800 dark:hover:border-gray-600"
    >
      <div className="text-3xl mb-3">{icon}</div>
      <h2 className="font-semibold text-lg">{title}</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{description}</p>
    </Link>
  );
}
