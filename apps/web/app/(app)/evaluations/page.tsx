"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { evaluations } from "@/lib/api-client";
import { toast } from "sonner";
import {
  PageHeader,
  Surface,
  StatusChip,
  HelioButton,
  EmptyState,
  Skeleton,
  Eyebrow,
} from "@/components/helio";

export default function EvaluationsPage() {
  const queryClient = useQueryClient();

  const { data: runs, isLoading, error } = useQuery({
    queryKey: ["evaluation-runs"],
    queryFn: evaluations.listRuns,
    retry: false,
  });

  const startMutation = useMutation({
    mutationFn: () => evaluations.startRun({ suite: "curated", max_cases: 10 }),
    onSuccess: (data) => {
      toast.success(`Eval run ${data.run_id?.slice(0, 8) || ""} completed`, {
        description: `${data.passed ?? 0} passed · ${data.failed ?? 0} failed`,
      });
      void queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] });
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Failed to start evaluation");
    },
  });

  if ((error as { status?: number } | null)?.status === 403) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Quality"
          title="Evaluations"
          description="Test assistant performance, policy compliance, and diagnostic accuracy."
        />
        <Surface>
          <EmptyState
            title="Access restricted"
            description="The evaluation console is available to IT and admin roles."
          />
        </Surface>
      </div>
    );
  }

  const runList = Array.isArray(runs) ? runs : [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Quality"
        title="Evaluations"
        description="Test assistant performance, policy compliance, and diagnostic accuracy."
        actions={
          <HelioButton
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending}
            loading={startMutation.isPending}
          >
            {startMutation.isPending ? "Running…" : "Run curated suite"}
          </HelioButton>
        }
      />

      <Surface className="p-5 sm:p-6">
        <Eyebrow className="mb-4">Evaluation runs</Eyebrow>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : runList.length === 0 ? (
          <EmptyState
            title="No evaluation runs yet"
            description="Start the curated suite to populate results."
          />
        ) : (
          <ul className="space-y-3">
            {runList.map(
              (run: {
                run_id: string;
                started_at?: string;
                provider?: string;
                passed_tests?: number;
                total_tests?: number;
                failed_tests?: number;
                status?: string;
              }) => (
                <li
                  key={run.run_id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-[var(--stroke)] p-4"
                >
                  <div>
                    <p className="font-mono text-sm text-[var(--ink)]">{run.run_id}</p>
                    <p className="text-xs text-[var(--ink-tertiary)] mt-1">
                      {run.started_at ? new Date(run.started_at).toLocaleString() : "-"} ·{" "}
                      {run.provider || "simulator"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm tabular-nums text-[var(--ink-secondary)]">
                      {run.passed_tests ?? 0}/{run.total_tests ?? 0} passed
                    </span>
                    <StatusChip tone={run.failed_tests ? "warning" : "success"}>
                      {run.status || "completed"}
                    </StatusChip>
                  </div>
                </li>
              )
            )}
          </ul>
        )}
      </Surface>
    </div>
  );
}
