"use client";

import Link from "next/link";

import ScenarioIcon from "@/components/ScenarioIcon";
import { scenarios } from "@/lib/scenarios";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
        {/* ---------------------------------------------------------------- */}
        {/* HEADER                                                           */}
        {/* ---------------------------------------------------------------- */}

        <header className="flex items-center justify-between border-b border-zinc-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white font-bold text-black">
              A
            </div>

            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                ARBITER
              </h1>

              <p className="text-xs text-zinc-500">
                Trust-aware agentic commerce
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />

            <span className="text-xs font-medium text-emerald-300">
              SYSTEM ONLINE
            </span>
          </div>
        </header>

        {/* ---------------------------------------------------------------- */}
        {/* HERO                                                             */}
        {/* ---------------------------------------------------------------- */}

        <section className="py-12">
          <p className="text-xs uppercase tracking-[0.25em] text-zinc-500">
            Demonstration environment
          </p>

          <h2 className="mt-3 text-4xl font-semibold tracking-tight lg:text-5xl">
            Choose an Arbiter scenario
          </h2>

          <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
            Explore how Arbiter changes agent autonomy according to buyer
            trust, merchant constraints, negotiation conditions, and final
            transaction authorization.
          </p>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* SCENARIOS                                                        */}
        {/* ---------------------------------------------------------------- */}

        <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {scenarios.map((scenario) => (
            <Link
              key={scenario.id}
              href={`/scenario/${scenario.id}`}
              className="group rounded-2xl border border-zinc-800 bg-zinc-950 p-6 transition duration-200 hover:-translate-y-1 hover:border-zinc-600 hover:bg-zinc-900"
            >
              {/* ICON */}

              <div className="flex items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900 text-zinc-400 transition-colors duration-200 group-hover:border-zinc-700 group-hover:bg-zinc-800 group-hover:text-white">
                  <ScenarioIcon icon={scenario.icon} />
                </div>

                <span className="text-zinc-600 transition-colors duration-200 group-hover:text-zinc-300">
                  →
                </span>
              </div>

              {/* LABEL */}

              <p className="mt-6 text-xs uppercase tracking-[0.18em] text-zinc-500">
                {scenario.shortTitle}
              </p>

              {/* TITLE */}

              <h3 className="mt-2 text-xl font-semibold tracking-tight">
                {scenario.title}
              </h3>

              {/* DESCRIPTION */}

              <p className="mt-3 min-h-[72px] text-sm leading-6 text-zinc-400">
                {scenario.description}
              </p>

              {/* DEMONSTRATION */}

              <div className="mt-6 border-t border-zinc-800 pt-4">
                <p className="text-xs leading-5 text-zinc-500">
                  {scenario.demonstration}
                </p>
              </div>

              {/* CTA */}

              <div className="mt-5 flex items-center text-sm font-medium text-white">
                Try scenario

                <span className="ml-2 transition-all duration-200 group-hover:ml-3">
                  →
                </span>
              </div>
            </Link>
          ))}
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* DASHBOARD METRICS                                                */}
        {/* ---------------------------------------------------------------- */}

        <section className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <DashboardMetric
              label="Scenarios"
              value={String(scenarios.length)}
            />

            <DashboardMetric
              label="Decision model"
              value="Trust-aware"
            />

            <DashboardMetric
              label="Authorization"
              value="Deterministic"
            />
          </div>
        </section>
      </div>
    </main>
  );
}

function DashboardMetric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.18em] text-zinc-600">
        {label}
      </p>

      <p className="mt-2 text-xl font-semibold text-zinc-100">
        {value}
      </p>
    </div>
  );
}