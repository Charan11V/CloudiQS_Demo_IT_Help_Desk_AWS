"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { devices } from "@/lib/api-client";
import { MonitorSmartphone, Cpu, HardDrive, Activity, RefreshCw } from "lucide-react";
import {
  PageHeader,
  Surface,
  StatusChip,
  HelioButton,
  EmptyState,
  Skeleton,
} from "@/components/helio";

function deviceStatusTone(status?: string): "success" | "warning" | "danger" | "neutral" {
  const s = (status || "").toLowerCase();
  if (["active", "healthy", "assigned", "compliant"].includes(s)) return "success";
  if (["warning", "degraded"].includes(s)) return "warning";
  if (["offline", "noncompliant", "failed"].includes(s)) return "danger";
  return "neutral";
}

export default function DevicesPage() {
  const queryClient = useQueryClient();
  const { data: deviceList, isLoading, isFetching } = useQuery({
    queryKey: ["devices"],
    queryFn: devices.list,
  });

  const list = deviceList || [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Environment"
        title="Your devices"
        description="Hardware assigned to you, with health and compliance from your tenant."
        actions={
          <HelioButton
            variant="secondary"
            size="sm"
            disabled={isFetching}
            onClick={() => void queryClient.invalidateQueries({ queryKey: ["devices"] })}
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </HelioButton>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Skeleton className="h-56" />
          <Skeleton className="h-56" />
        </div>
      ) : list.length === 0 ? (
        <Surface>
          <EmptyState
            title="No devices assigned"
            description="Assigned hardware will appear here when available from your directory."
          />
        </Surface>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {list.map(
            (device: {
              device_id: string;
              device_name?: string;
              hostname?: string;
              model?: string;
              device_type?: string;
              status?: string;
              lifecycle?: string;
              os?: string;
              site?: string;
              serial?: string;
              serial_number?: string;
              cpu_percent?: number | null;
              disk_free_gb?: number | null;
              disk_free_percent?: number | null;
              compliance_state?: string;
              compliant?: boolean;
            }) => {
              const noncompliant =
                device.compliance_state === "noncompliant" || device.compliant === false;
              const subtitle = [
                device.model,
                device.device_type
                  ? device.device_type.charAt(0).toUpperCase() + device.device_type.slice(1)
                  : null,
                device.os,
                device.site,
              ]
                .filter(Boolean)
                .join(" · ");
              return (
                <Surface key={device.device_id} className="p-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-11 w-11 rounded-xl bg-[var(--signal-soft)] flex items-center justify-center text-[var(--signal)] shrink-0">
                        <MonitorSmartphone className="w-5 h-5" strokeWidth={1.75} />
                      </div>
                      <div className="min-w-0">
                        <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--ink)] truncate">
                          {device.hostname || device.device_name || device.device_id}
                        </h2>
                        <p className="text-sm text-[var(--ink-secondary)]">
                          {subtitle || "Corporate device"}
                        </p>
                      </div>
                    </div>
                    <StatusChip tone={deviceStatusTone(device.status || device.lifecycle)}>
                      {device.status || device.lifecycle || "active"}
                    </StatusChip>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-[var(--ink-secondary)] mb-1">Operating system</p>
                      <p className="font-medium text-[var(--ink)]">{device.os || "-"}</p>
                    </div>
                    <div>
                      <p className="text-[var(--ink-secondary)] mb-1">Serial number</p>
                      <p className="font-mono text-xs text-[var(--ink)]">
                        {device.serial || device.serial_number || "N/A"}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-[var(--ink-secondary)]">
                        <Cpu className="w-4 h-4" />
                        <span>CPU usage</span>
                      </div>
                      <span className="font-medium tabular-nums text-[var(--ink)]">
                        {device.cpu_percent != null ? `${device.cpu_percent}%` : "Normal"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-[var(--ink-secondary)]">
                        <HardDrive className="w-4 h-4" />
                        <span>Disk space</span>
                      </div>
                      <span className="font-medium tabular-nums text-[var(--ink)]">
                        {device.disk_free_gb != null
                          ? `${device.disk_free_gb} GB free`
                          : device.disk_free_percent != null
                            ? `${device.disk_free_percent}% free`
                            : "Adequate"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-[var(--ink-secondary)]">
                        <Activity className="w-4 h-4" />
                        <span>Compliance</span>
                      </div>
                      <StatusChip tone={noncompliant ? "danger" : "success"}>
                        {device.compliance_state ||
                          (device.compliant === false ? "Noncompliant" : "Compliant")}
                      </StatusChip>
                    </div>
                  </div>
                </Surface>
              );
            }
          )}
        </div>
      )}
    </div>
  );
}
