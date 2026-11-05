"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  X,
  AlertOctagon,
  AlertTriangle,
  TrendingDown,
  CheckCircle2,
  Clock,
  RefreshCw,
  Check,
  Undo2,
  Bell,
  Scan,
} from "lucide-react";
import {
  AnomalyHistoryResponse,
  AnomalyEventItem,
  AnomalySeverity,
} from "@/lib/types";
import {
  fetchAnomalyHistory,
  resolveAnomalyEvent,
  scanHistoricalAnomalies,
} from "@/lib/api";
import { formatUtcDateTime } from "@/lib/formatters";

interface AnomalyAlertLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAlertUpdated?: () => void;
}

export function AnomalyAlertLogModal({
  isOpen,
  onClose,
  onAlertUpdated,
}: AnomalyAlertLogModalProps) {
  const [data, setData] = useState<AnomalyHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "RESOLVED">("ALL");
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAnomalyHistory({
        severity: severityFilter === "ALL" ? undefined : severityFilter,
        resolved:
          statusFilter === "ALL"
            ? undefined
            : statusFilter === "RESOLVED",
        limit: 100,
      });
      setData(res);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to load anomaly alert log.");
    } finally {
      setLoading(false);
    }
  }, [severityFilter, statusFilter]);

  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        loadAlerts();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isOpen, loadAlerts]);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleToggleResolve = async (event: AnomalyEventItem) => {
    try {
      const res = await resolveAnomalyEvent(event.id, !event.resolved);
      setData((prev) => {
        if (!prev) return null;
        const updatedEvents = prev.events.map((e) =>
          e.id === event.id
            ? {
                ...e,
                resolved: res.resolved,
                resolved_at: res.resolved_at,
              }
            : e
        );
        const newlyResolved = res.resolved && !event.resolved;
        return {
          ...prev,
          events: updatedEvents,
          summary: {
            ...prev.summary,
            resolved_count: newlyResolved
              ? prev.summary.resolved_count + 1
              : prev.summary.resolved_count - 1,
            unresolved_count: newlyResolved
              ? prev.summary.unresolved_count - 1
              : prev.summary.unresolved_count + 1,
          },
        };
      });
      if (onAlertUpdated) onAlertUpdated();
    } catch (err) {
      alert(`Failed to update alert status: ${(err as Error)?.message}`);
    }
  };

  const handleScanHistory = async () => {
    setIsScanning(true);
    setScanMessage(null);
    try {
      const res = await scanHistoricalAnomalies();
      setScanMessage(
        res.new_anomalies_recorded > 0
          ? `Scanned all telemetry: recorded ${res.new_anomalies_recorded} new anomalies!`
          : "Scan complete: all historical anomalies already cataloged."
      );
      loadAlerts();
      if (onAlertUpdated) onAlertUpdated();
    } catch (err) {
      setScanMessage(`Scan error: ${(err as Error)?.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  if (!isOpen) return null;

  const summary = data?.summary;

  const severityBadge = (severity: AnomalySeverity) => {
    switch (severity) {
      case "CRITICAL_SURGE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-[#FFF5F5] border border-[#F87171] text-[#B91C1C]">
            <AlertOctagon className="w-3.5 h-3.5 text-[#C92A2A]" />
            Critical Surge
          </span>
        );
      case "MODERATE_SURGE":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-[#FFFBEB] border border-[#D9730D] text-[#92400E]">
            <AlertTriangle className="w-3.5 h-3.5 text-[#D9730D]" />
            Moderate Surge
          </span>
        );
      case "MODERATE_DROP":
      case "UNUSUAL_DROP":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-[#F8FAFC] border border-[#94A3B8] text-[#334155]">
            <TrendingDown className="w-3.5 h-3.5 text-[#64748B]" />
            Volume Drop
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[#F0FDF4] border border-[#4ADE80] text-[#166534]">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2B8A3E]" />
            Normal
          </span>
        );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-log-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="bg-white rounded border border-[#D5DFDB] max-w-4xl w-full p-6 shadow-xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#D5DFDB] shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-[#B91C1C]/10 text-[#B91C1C] flex items-center justify-center shrink-0">
                <Bell className="w-4 h-4" aria-hidden="true" />
              </div>
              <div>
                <h2
                  id="alert-log-title"
                  className="font-heading text-lg font-bold text-[#122B32]"
                >
                  Anomaly History & Operational Alert Log
                </h2>
                <p className="text-xs text-[#4A6369]">
                  Persistent audit log of all detected arrival surges, drops, and resolution states.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#4A6369] hover:text-[#122B32] p-1.5 rounded transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Aggregate KPI Strip */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 py-3 border-b border-[#D5DFDB] shrink-0 bg-[#F3F6F4]/50 -mx-6 px-6">
            <div className="text-center p-2 rounded bg-white border border-[#D5DFDB]">
              <span className="text-[11px] text-[#4A6369] block">Total Logged</span>
              <span className="font-heading text-lg font-bold text-[#122B32]">
                {summary.total_anomalies}
              </span>
            </div>
            <div className="text-center p-2 rounded bg-white border border-[#F87171]/40">
              <span className="text-[11px] text-[#B91C1C] block font-medium">Critical Surges</span>
              <span className="font-heading text-lg font-bold text-[#B91C1C]">
                {summary.critical_surges}
              </span>
            </div>
            <div className="text-center p-2 rounded bg-white border border-[#D9730D]/40">
              <span className="text-[11px] text-[#92400E] block font-medium">Moderate Surges</span>
              <span className="font-heading text-lg font-bold text-[#D9730D]">
                {summary.moderate_surges}
              </span>
            </div>
            <div className="text-center p-2 rounded bg-white border border-[#D5DFDB]">
              <span className="text-[11px] text-[#4A6369] block">Volume Drops</span>
              <span className="font-heading text-lg font-bold text-[#334155]">
                {summary.drops}
              </span>
            </div>
            <div className="text-center p-2 rounded bg-white border border-[#D5DFDB]">
              <span className="text-[11px] text-[#0A6E73] block font-medium">Active Unresolved</span>
              <span className="font-heading text-lg font-bold text-[#0A6E73]">
                {summary.unresolved_count}
              </span>
            </div>
          </div>
        )}

        {/* Filter and Action Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-3 border-b border-[#D5DFDB] shrink-0">
          {/* Severity & Status Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded border border-[#D5DFDB] p-0.5 bg-[#F3F6F4]">
              {(
                [
                  { id: "ALL", label: "All" },
                  { id: "CRITICAL_SURGE", label: "Critical" },
                  { id: "MODERATE_SURGE", label: "Moderate" },
                  { id: "MODERATE_DROP", label: "Drops" },
                ] as const
              ).map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setSeverityFilter(f.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                    severityFilter === f.id
                      ? "bg-white text-[#122B32] shadow-xs"
                      : "text-[#4A6369] hover:text-[#122B32]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="inline-flex rounded border border-[#D5DFDB] p-0.5 bg-[#F3F6F4]">
              {(
                [
                  { id: "ALL", label: "All Status" },
                  { id: "ACTIVE", label: "Unresolved" },
                  { id: "RESOLVED", label: "Resolved" },
                ] as const
              ).map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setStatusFilter(s.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                    statusFilter === s.id
                      ? "bg-white text-[#122B32] shadow-xs"
                      : "text-[#4A6369] hover:text-[#122B32]"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Action: Scan History & Refresh */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleScanHistory}
              disabled={isScanning}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-[#F3F6F4] hover:bg-[#E5ECE9] text-[#122B32] border border-[#D5DFDB] transition-colors cursor-pointer disabled:opacity-50"
              title="Scans uploaded data rows to discover any uncataloged anomalies"
            >
              <Scan className={`w-3.5 h-3.5 text-[#0A6E73] ${isScanning ? "animate-spin" : ""}`} />
              <span>{isScanning ? "Scanning..." : "Scan Telemetry"}</span>
            </button>
            <button
              type="button"
              onClick={loadAlerts}
              disabled={loading}
              className="p-1.5 rounded text-[#4A6369] hover:text-[#122B32] border border-[#D5DFDB] bg-white transition-colors cursor-pointer"
              title="Refresh alert log"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Scan Message Alert */}
        {scanMessage && (
          <div className="p-2.5 text-xs bg-[#F0FDF4] border-b border-[#4ADE80] text-[#166534] flex items-center justify-between">
            <span>{scanMessage}</span>
            <button
              type="button"
              onClick={() => setScanMessage(null)}
              className="text-[#166534] font-bold text-xs"
            >
              ✕
            </button>
          </div>
        )}

        {/* Alert Events Timeline List */}
        <div className="flex-1 overflow-y-auto divide-y divide-[#D5DFDB] -mx-6 px-6">
          {loading && (
            <div className="py-12 text-center text-sm text-[#4A6369]">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0A6E73]" />
              Loading anomaly audit log...
            </div>
          )}

          {error && (
            <div className="p-4 my-4 bg-[#FFF5F5] border border-[#F87171] text-[#B91C1C] rounded text-sm text-center">
              {error}
            </div>
          )}

          {!loading && !error && (!data?.events || data.events.length === 0) && (
            <div className="py-16 text-center text-[#4A6369]">
              <CheckCircle2 className="w-10 h-10 text-[#0A6E73]/50 mx-auto mb-3" />
              <h3 className="font-heading text-base font-bold text-[#122B32]">
                No anomaly alert events found
              </h3>
              <p className="text-xs text-[#4A6369] mt-1 max-w-sm mx-auto">
                No events match the selected filters. Use &quot;Scan Telemetry&quot; to backfill past surge events from uploaded data.
              </p>
            </div>
          )}

          {!loading &&
            !error &&
            data?.events &&
            data.events.map((event) => (
              <div
                key={event.id}
                className={`py-3.5 transition-colors ${
                  event.resolved ? "opacity-60 bg-[#F8FAFC]/50" : "hover:bg-[#F3F6F4]/40"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  {/* Left: Metadata & Severity */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {severityBadge(event.severity)}
                      <span className="font-mono text-xs font-semibold text-[#122B32] flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-[#0A6E73]" />
                        {formatUtcDateTime(event.timestamp)}
                      </span>
                      {event.resolved ? (
                        <span className="text-[11px] font-semibold text-[#166534] bg-[#F0FDF4] px-2 py-0.5 rounded border border-[#4ADE80]">
                          ✓ Acknowledged
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold text-[#B91C1C] bg-[#FFF5F5] px-2 py-0.5 rounded border border-[#F87171]">
                          ● Open Alert
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-[#122B32] mt-1 leading-relaxed">
                      {event.explanation}
                    </p>

                    <div className="flex items-center gap-4 text-[11px] text-[#4A6369] pt-1">
                      <span>
                        Observed: <strong className="text-[#122B32]">{event.observed_value}</strong> arrivals
                      </span>
                      <span>·</span>
                      <span>
                        Baseline: <strong className="text-[#122B32]">{event.expected_baseline}</strong>
                      </span>
                      <span>·</span>
                      <span>
                        Deviation:{" "}
                        <strong
                          className={event.deviation_pct >= 0 ? "text-[#C92A2A]" : "text-[#2563EB]"}
                        >
                          {event.deviation_pct >= 0 ? `+${event.deviation_pct}%` : `${event.deviation_pct}%`}
                        </strong>
                      </span>
                    </div>
                  </div>

                  {/* Right: Resolve / Acknowledge Action Button */}
                  <div className="shrink-0 pt-1 sm:pt-0">
                    <button
                      type="button"
                      onClick={() => handleToggleResolve(event)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                        event.resolved
                          ? "bg-white border border-[#D5DFDB] text-[#4A6369] hover:text-[#122B32]"
                          : "bg-[#0A6E73] hover:bg-[#08565A] text-white"
                      }`}
                    >
                      {event.resolved ? (
                        <>
                          <Undo2 className="w-3.5 h-3.5" />
                          <span>Reopen</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>Acknowledge</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-[#D5DFDB] shrink-0 flex items-center justify-between text-xs text-[#4A6369]">
          <span>
            Events are persisted to SQLite <code className="font-mono text-[#122B32]">anomaly_events</code> table.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#122B32] text-white text-xs font-semibold hover:bg-black transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
