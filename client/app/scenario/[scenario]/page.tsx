"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import NegotiationDemo from "@/components/NegotiationDemo";
import ScenarioIcon from "@/components/ScenarioIcon";
import { getScenario } from "@/lib/scenarios";

export default function ScenarioPage() {
  const params = useParams();

  const scenarioId = String(params.scenario);

  const scenario = getScenario(scenarioId);

  if (!scenario) {
    return (
      <main className="min-h-screen bg-[#0a0a0a] text-white">
        <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
          <Link
            href="/"
            className="text-sm text-zinc-400 transition hover:text-white"
          >
            ← All scenarios
          </Link>

          <div className="mt-12 rounded-2xl border border-red-900/50 bg-red-950/20 p-6">
            <p className="text-sm font-semibold text-red-300">
              Scenario not found
            </p>

            <p className="mt-2 text-sm text-red-400">
              The requested Arbiter scenario does not exist.
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
        {/* ---------------------------------------------------------------- */}
        {/* HEADER                                                           */}
        {/* ---------------------------------------------------------------- */}

        <header className="flex items-center justify-between border-b border-zinc-800 pb-6">
          <Link
            href="/"
            className="text-sm text-zinc-400 transition hover:text-white"
          >
            ← All scenarios
          </Link>

          <div className="flex items-center gap-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />

            <span className="text-xs font-medium text-emerald-300">
              SYSTEM ONLINE
            </span>
          </div>
        </header>

        {/* ---------------------------------------------------------------- */}
        {/* SCENARIO HEADER                                                  */}
        {/* ---------------------------------------------------------------- */}

        <section className="py-10">
          <div className="flex items-start gap-5">
            {/* PROFESSIONAL SCENARIO ICON */}

            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-zinc-800 bg-zinc-950 text-zinc-300">
              <ScenarioIcon icon={scenario.icon} />
            </div>

            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-zinc-500">
                Arbiter Scenario
              </p>

              <h1 className="mt-2 text-4xl font-semibold tracking-tight lg:text-5xl">
                {scenario.title}
              </h1>

              <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
                {scenario.description}
              </p>
            </div>
          </div>

          {/* DEMONSTRATION */}

          <div className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
              Demonstrates
            </p>

            <p className="mt-2 text-sm leading-6 text-zinc-300">
              {scenario.demonstration}
            </p>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* NEGOTIATION ENGINE                                               */}
        {/* ---------------------------------------------------------------- */}

        <NegotiationDemo scenario={scenario} />
      </div>
    </main>
  );
}