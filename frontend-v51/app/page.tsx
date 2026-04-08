import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-full flex-1 flex-col items-center justify-center bg-gray-50 px-6 py-24 dark:bg-gray-950">
      <div className="max-w-lg text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-blue-600 dark:text-blue-400">
          Save the Children International · Mali
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
          Decision Memory System
        </h1>
        <p className="mt-4 text-gray-600 dark:text-gray-400">
          Pilotage des marchés publics, délibération et traçabilité — sans
          recommandation automatisée (Canon DMS).
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex w-full items-center justify-center rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 sm:w-auto"
          >
            Connexion
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex w-full items-center justify-center rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-800 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:hover:bg-gray-800 sm:w-auto"
          >
            Tableau de bord
          </Link>
        </div>
      </div>
    </div>
  );
}
