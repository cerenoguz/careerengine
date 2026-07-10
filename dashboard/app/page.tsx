"use client";

import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";

type Filter = "new" | "best_fit" | "not_viewed";

type Job = {
  job_id: string;
  company: string;
  title: string;
  location: string | null;
  url: string;
  source: string | null;
  first_found_date: string;
  last_seen_date: string;
  is_active: boolean;
  current_rank: number | null;
  bucket: "apply_now" | "review" | "archive" | "exclude";
  final_score: number | null;
  ai_profile_fit: number | null;
  profile_fit_band: string | null;
  work_auth_review: string | null;
  opportunity_type: string | null;
  reason: string | null;
  viewed_at: string | null;
  applied_at: string | null;
  not_applied_at: string | null;
  not_applied_reason: string | null;
  archived_at: string | null;
};

const filters: { key: Filter; label: string }[] = [
  { key: "new", label: "New" },
  { key: "best_fit", label: "Best Fit" },
  { key: "not_viewed", label: "Not Viewed" },
];

const reasons = [
  ["too_senior", "Too senior"],
  ["weak_fit", "Weak fit"],
  ["work_authorization_concern", "Work authorization concern"],
  ["bad_location", "Bad location"],
  ["not_interested_in_role", "Not interested in role"],
  ["job_closed_or_link_issue", "Job closed / link issue"],
] as const;

function todayString() {
  return new Date().toISOString().slice(0, 10);
}

function bucketLabel(bucket: Job["bucket"]) {
  if (bucket === "apply_now") return "Apply now";
  if (bucket === "review") return "Review";
  if (bucket === "archive") return "Lower priority";
  return "Excluded";
}

function bucketClass(bucket: Job["bucket"]) {
  if (bucket === "apply_now") return "bg-[#FBE3EB] text-[#8E4E5B] ring-[#FBE3EB]";
  if (bucket === "review") return "bg-[#FBE3EB] text-[#8E4E5B] ring-[#FBE3EB]";
  if (bucket === "archive") return "bg-stone-100 text-stone-600 ring-stone-200";
  return "bg-red-50 text-red-700 ring-red-100";
}
type FitStatus = "yes" | "no" | "maybe";

function formatAiFit(job: Job) {
  if (job.ai_profile_fit !== null && job.ai_profile_fit !== undefined) {
    return `${job.ai_profile_fit.toFixed(1)}% Match`;
  }

  if (job.final_score !== null && job.final_score !== undefined) {
    return `${job.final_score.toFixed(1)}`;
  }

  return "—";
}

function getNewGradFitStatus(job: Job): FitStatus {
  const text = `${job.opportunity_type ?? ""} ${job.title ?? ""}`.toLowerCase();

  if (
    text.includes("new-grad") ||
    text.includes("new grad") ||
    text.includes("early-career") ||
    text.includes("early career") ||
    text.includes("internship") ||
    text.includes("intern")
  ) {
    return "yes";
  }

  if (
    text.includes("senior") ||
    text.includes("staff") ||
    text.includes("principal") ||
    text.includes("lead")
  ) {
    return "no";
  }

  return "maybe";
}

function getVisaFitStatus(job: Job): FitStatus {
  const text = (job.work_auth_review ?? "").toLowerCase();

  if (text.includes("likely compatible")) {
    return "yes";
  }

  if (text.includes("unclear") || text.includes("needs review") || !text) {
    return "maybe";
  }

  return "no";
}

function FitStatusRow({
  label,
  status,
}: {
  label: string;
  status: FitStatus;
}) {
  const symbol = status === "yes" ? "✓" : status === "no" ? "×" : "?";

  return (
    <div className="flex items-center gap-3">
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-[#F3C6CF] text-sm font-semibold leading-none text-[#F199AA]">
        {symbol}
      </span>
      <span className="text-[14px] font-medium text-stone-700">{label}</span>
    </div>
  );
}

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState<Filter>("best_fit");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actingJobId, setActingJobId] = useState<string | null>(null);

  const pageTitle = useMemo(() => {
    if (filter === "new") return "New opportunities";
    if (filter === "best_fit") return "Ranked qualified opportunities";
    return "Not viewed opportunities";
  }, [filter]);

  async function loadJobs(activeFilter = filter) {
    setLoading(true);
    setError(null);

    let query = supabase
      .from("careerengine_jobs")
      .select("*")
      .eq("is_active", true)
      .is("archived_at", null)
      .neq("bucket", "exclude");

    if (activeFilter === "new") {
      query = query.eq("first_found_date", todayString()).order("current_rank", {
        ascending: true,
        nullsFirst: false,
      });
    }

    if (activeFilter === "best_fit") {
      query = query
        .order("current_rank", { ascending: true, nullsFirst: false })
        .order("ai_profile_fit", { ascending: false, nullsFirst: false });
    }

    if (activeFilter === "not_viewed") {
      query = query
        .is("viewed_at", null)
        .order("current_rank", { ascending: true, nullsFirst: false });
    }

    const { data, error: queryError } = await query.limit(500);

    if (queryError) {
      setError(queryError.message);
      setJobs([]);
    } else {
      setJobs((data ?? []) as Job[]);
    }

    setLoading(false);
  }

  useEffect(() => {
    loadJobs(filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function markViewed(job: Job) {
    if (job.viewed_at) return;

    const now = new Date().toISOString();

    await supabase
      .from("careerengine_jobs")
      .update({ viewed_at: now, updated_at: now })
      .eq("job_id", job.job_id);

    await supabase.from("careerengine_job_actions").insert({
      job_id: job.job_id,
      action: "viewed",
    });
  }

  async function openJob(job: Job) {
    setActingJobId(job.job_id);
    await markViewed(job);
    window.open(job.url, "_blank", "noopener,noreferrer");
    await loadJobs(filter);
    setActingJobId(null);
  }

  async function markApplied(job: Job) {
    setActingJobId(job.job_id);
    const now = new Date().toISOString();

    await supabase
      .from("careerengine_jobs")
      .update({
        viewed_at: job.viewed_at ?? now,
        applied_at: now,
        updated_at: now,
      })
      .eq("job_id", job.job_id);

    await supabase.from("careerengine_job_actions").insert({
      job_id: job.job_id,
      action: "applied",
    });

    await loadJobs(filter);
    setActingJobId(null);
  }

  async function markNotApplied(job: Job, reason: string) {
    if (!reason) return;

    setActingJobId(job.job_id);
    const now = new Date().toISOString();

    await supabase
      .from("careerengine_jobs")
      .update({
        viewed_at: job.viewed_at ?? now,
        not_applied_at: now,
        not_applied_reason: reason,
        archived_at: now,
        updated_at: now,
      })
      .eq("job_id", job.job_id);

    await supabase.from("careerengine_job_actions").insert({
      job_id: job.job_id,
      action: "not_applied",
      reason,
    });

    await loadJobs(filter);
    setActingJobId(null);
  }

  return (
    <main className="min-h-screen bg-[#f7f4ef] px-5 py-8 text-stone-950">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 rounded-3xl border border-stone-200 bg-white/80 p-6 shadow-sm shadow-stone-200/60 backdrop-blur">
          <div className="mb-8 flex items-center justify-between gap-4">
            <div>
              <div className="text-xl font-semibold tracking-[-0.05em] text-[#2B2927]">
                CareerEngine <span className="text-[#D98E9B]">.</span>{" "}
                <span className="font-serif text-base font-normal italic tracking-normal text-[#766F6A]">
                  by Ceren Oguz
                </span>
              </div>
            </div>

            <div className="hidden rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-xs font-medium text-stone-500 sm:block">
              Supabase Dashboard
            </div>
          </div>

          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.28em] text-[#D98E9B]">
            AI-assisted job discovery pipeline
          </p>
          <h1 className="max-w-4xl text-2xl font-semibold tracking-tight text-stone-950 sm:text-3xl lg:text-4xl">
            Manage your ranked job opportunities.
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-stone-600">
            Review qualified roles, track application decisions, and maintain a focused
            opportunity queue as CareerEngine refreshes and re-ranks postings.
          </p>
        </header>

        <section className="mb-6 flex flex-wrap gap-2">
          {filters.map((item) => (
            <button
              key={item.key}
              onClick={() => setFilter(item.key)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                filter === item.key
                  ? "bg-stone-950 text-white shadow-sm"
                  : "border border-stone-200 bg-white text-stone-600 hover:border-stone-300 hover:bg-stone-50"
              }`}
            >
              {item.label}
            </button>
          ))}
        </section>

        <section className="mb-5 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-stone-950">{pageTitle}</h2>
            <p className="mt-1 text-sm text-stone-500">
              Showing {jobs.length} job{jobs.length === 1 ? "" : "s"}
            </p>
          </div>

          <button
            onClick={() => loadJobs(filter)}
            className="rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-600 shadow-sm hover:bg-stone-50"
          >
            Refresh
          </button>
        </section>

        {loading && (
          <div className="rounded-2xl border border-stone-200 bg-white p-5 text-sm text-stone-500 shadow-sm">
            Loading opportunities...
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-sm">
            {error}
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="rounded-2xl border border-stone-200 bg-white p-5 text-sm text-stone-500 shadow-sm">
            No opportunities in this view.
          </div>
        )}

        <div className="space-y-4">
          {jobs.map((job) => (
            <article
              key={job.job_id}
              className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm shadow-stone-200/70 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="mb-3 flex flex-wrap gap-2">
                    <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-600 ring-1 ring-stone-200">
                      Rank #{job.current_rank ?? "—"}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${bucketClass(
                        job.bucket
                      )}`}
                    >
                      {bucketLabel(job.bucket)}
                    </span>
                    {job.opportunity_type && (
                      <span className="rounded-full bg-[#FBE3EB] px-2.5 py-1 text-xs font-medium text-[#8E4E5B] ring-1 ring-[#FBE3EB]">
                        {job.opportunity_type}
                      </span>
                    )}
                  </div>

                  <h3 className="text-lg font-semibold leading-snug text-stone-950">
                    {job.company} — {job.title}
                  </h3>

                  <p className="mt-1 text-sm text-stone-500">
                    {job.location || "Location not listed"}
                  </p>

                  <div className="mt-4 grid gap-3 text-sm text-stone-600 sm:grid-cols-3">
                    <div className="rounded-2xl bg-stone-50 px-5 py-4">
                      <span className="block text-xs font-medium uppercase tracking-wide text-stone-400">
                        AI Fit
                      </span>
                      <p className="mt-2 text-[15px] font-medium text-stone-700">
                        {formatAiFit(job)}
                      </p>
                    </div>

                    <div className="rounded-2xl bg-stone-50 px-5 py-4">
                      <div className="flex flex-col gap-2">
                        <FitStatusRow
                          label="New Grad"
                          status={getNewGradFitStatus(job)}
                        />
                        <FitStatusRow
                          label="Visa"
                          status={getVisaFitStatus(job)}
                        />
                      </div>
                    </div>

                    <div className="rounded-2xl bg-stone-50 px-5 py-4">
                      <span className="block text-xs font-medium uppercase tracking-wide text-stone-400">
                        First Found
                      </span>
                      <p className="mt-2 text-[15px] font-medium text-stone-700">
                        {job.first_found_date}
                      </p>
                    </div>
                  </div>

                  {job.reason && (
                    <p className="mt-4 line-clamp-3 text-sm leading-6 text-stone-500">
                      {job.reason}
                    </p>
                  )}
                </div>

                <div className="flex min-w-48 flex-col gap-2">
                  <button
                    disabled={actingJobId === job.job_id}
                    onClick={() => openJob(job)}
                    className="rounded-xl bg-stone-950 px-4 py-2.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
                  >
                    Open Link
                  </button>

                  <button
                    disabled={actingJobId === job.job_id}
                    onClick={() => {
                      if (!job.applied_at) {
                        markApplied(job);
                      }
                    }}
                    className={`rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:opacity-50 ${
                      job.applied_at
                        ? "cursor-default border border-stone-200 bg-white text-stone-950"
                        : "bg-[#F199AA] text-white hover:bg-[#E58A9B]"
                    }`}
                  >
                    {job.applied_at ? "Applied" : "Apply"}
                  </button>

                  <select
                    disabled={actingJobId === job.job_id}
                    defaultValue=""
                    onChange={(event) => markNotApplied(job, event.target.value)}
                    className="rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-600 shadow-sm disabled:opacity-50"
                  >
                    <option value="" disabled>
                      Not Applied...
                    </option>
                    {reasons.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
