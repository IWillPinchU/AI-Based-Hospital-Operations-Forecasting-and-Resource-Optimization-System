import React from "react";
import { Activity, Upload, Clock, RefreshCw, WifiOff } from "lucide-react";
import { formatUtcDateTime } from "@/lib/formatters";

interface NavbarProps {
  latestTimestamp?: string | null;
  onOpenUpload: () => void;
  isIngesting?: boolean;
  lastRefreshedAt?: Date | null;
  livePaused?: boolean;
}

function formatLocalTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function Navbar({
  latestTimestamp,
  onOpenUpload,
  isIngesting,
  lastRefreshedAt,
  livePaused,
}: NavbarProps) {
  return (
    <header className="bg-white border-b border-[#D5DFDB] sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Title and Hospital Signage Icon */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded bg-[#0A6E73] text-white flex items-center justify-center shrink-0">
            <Activity className="w-5 h-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="font-heading text-lg sm:text-xl font-bold text-[#122B32] truncate">
              Hospital Operations Forecasting and Resource Optimization System
            </h1>
            <p className="text-xs text-[#4A6369] truncate">
              Emergency department decision support and capacity telemetry
            </p>
          </div>
        </div>

        {/* Timestamp and Ingestion Button */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#4A6369] bg-[#F3F6F4] px-3 py-1.5 rounded border border-[#D5DFDB] whitespace-nowrap">
            <Clock className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
            <span>Latest data:</span>
            <span className="font-semibold text-[#122B32]">
              {formatUtcDateTime(latestTimestamp)}
            </span>
          </div>

          {lastRefreshedAt && (
            <div className="hidden xl:flex items-center gap-1.5 text-xs text-[#4A6369] bg-[#F3F6F4] px-3 py-1.5 rounded border border-[#D5DFDB] whitespace-nowrap">
              <RefreshCw className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
              <span>Last refreshed:</span>
              <span className="font-semibold text-[#122B32]">
                {formatLocalTime(lastRefreshedAt)}
              </span>
            </div>
          )}

          <button
            type="button"
            onClick={onOpenUpload}
            disabled={isIngesting}
            className="inline-flex items-center gap-2 bg-[#0A6E73] hover:bg-[#08565A] text-white text-sm font-semibold px-3.5 py-2 rounded transition-colors shadow-none focus-visible:ring-2 focus-visible:ring-[#0A6E73] cursor-pointer disabled:opacity-60"
          >
            <Upload className="w-4 h-4" aria-hidden="true" />
            <span>Upload CSV</span>
          </button>
        </div>
      </div>
      <div role="status" aria-live="polite">
        {livePaused && (
          <div className="bg-[#FFFBEB] border-t border-[#D9730D]/30 px-4 py-2 text-xs text-[#92400E] flex items-center justify-center gap-2">
            <WifiOff className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <span>Live updates paused. Showing last data.</span>
          </div>
        )}
      </div>
    </header>
  );
}
