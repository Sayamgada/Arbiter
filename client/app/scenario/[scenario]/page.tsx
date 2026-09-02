"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import NegotiationDemo from "@/components/NegotiationDemo";
import { getScenario } from "@/lib/scenarios";

export default function ScenarioPage() {
  const params = useParams();

  const scenarioId = Array.isArray(params.scenario)
    ? params.scenario[0]
    : params.scenario;

  const scenario = scenarioId ? getScenario(scenarioId) : undefined;

  if (!scenario) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0a0a0a] p-6 text-white">
        <div className="text-center">
          <p className="text-sm text-red-400">Scenario not found.</p>

          <Link
            href="/"
            className="mt-5 inline-block rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black"
          >
            Back to scenarios
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
        <header className="flex items-center justify-between border-b border-zinc-800 pb-6">
          <Link
            href="/"
            className="flex items-center gap-3 text-sm text-zinc-400 transition hover:text-white"
          >
            <span>←</span>
            <span>All scenarios</span>
          </Link>

          <div className="flex items-center gap-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />

            <span className="text-xs font-medium text-emerald-300">
              SYSTEM ONLINE
            </span>
          </div>
        </header>

        <section className="pt-10">
          <div className="flex items-start gap-4">
            <div className="text-4xl">{scenario.icon}</div>

            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-zinc-500">
                Arbiter Scenario
              </p>

              <h1 className="mt-2 text-4xl font-semibold tracking-tight">
                {scenario.title}
              </h1>

              <p className="mt-3 max-w-3xl text-zinc-400">
                {scenario.description}
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-950 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
              Demonstrates
            </p>

            <p className="mt-2 text-sm text-zinc-300">
              {scenario.demonstration}
            </p>
          </div>
        </section>

        <NegotiationDemo scenario={scenario} />
      </div>
    </main>
  );
}
