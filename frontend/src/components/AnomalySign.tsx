import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  TrendingDown,
  Info,
  Bell,
} from "lucide-react";
import { AnomalyResponse, AnomalySeverity } from "@/lib/types";

interface AnomalySignProps {
  data: AnomalyResponse | null;
  isLoading: boolean;
  error: string | null;
  onOpenAlertLog?: () => void;
  unresolvedAlertsCount?: number;
}

export function AnomalySign({
  data,
  isLoading,
  error,
  onOpenAlertLog,
  unresolvedAlertsCount,
}: AnomalySignProps) {
  if (isLoading) {
    return (
      <div className="bg-white border border-[#D5DFDB] rounded p-6 h-full flex items-center justify-center text-sm text-[#4A6369]">
        Evaluating historical hour-of-week baseline...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-white border border-[#D5DFDB] rounded p-6 h-full flex flex-col items-center justify-center text-center">
        <Info className="w-8 h-8 text-[#0A6E73] mb-2" aria-hidden="true" />
        <h3 className="font-heading text-base font-bold text-[#122B32]">
          Baseline calculation pending
        </h3>
        <p className="text-xs text-[#4A6369] mt-1 max-w-sm">
          {error || "Requires historical operational records for this day and hour."}
        </p>
      </div>
    );
  }

  // Triage configuration based on severity
  const severityConfig: Record<
    AnomalySeverity,
    {
      title: string;
      bgClass: string;
      borderClass: string;
      textClass: string;
      icon: React.ReactNode;
      badgeText: string;
    }
  > = {
    CRITICAL_SURGE: {
      title: "Critical arrival surge",
      bgClass: "bg-[#FFF5F5]",
      borderClass: "border-[#F87171]",
      textClass: "text-[#B91C1C]",
      icon: <AlertOctagon className="w-5 h-5 text-[#C92A2A]" aria-hidden="true" />,
      badgeText: "Critical surge",
    },
    MODERATE_SURGE: {
      title: "Moderate arrival surge",
      bgClass: "bg-[#FFFBEB]",
      borderClass: "border-[#D9730D]",
      textClass: "text-[#92400E]", // Darker amber passing contrast
      icon: <AlertTriangle className="w-5 h-5 text-[#D9730D]" aria-hidden="true" />,
      badgeText: "Moderate surge",
    },
    NORMAL: {
      title: "Normal arrival volume",
      bgClass: "bg-[#F0FDF4]",
      borderClass: "border-[#4ADE80]",
      textClass: "text-[#166534]",
      icon: <CheckCircle2 className="w-5 h-5 text-[#2B8A3E]" aria-hidden="true" />,
      badgeText: "Normal flow",
    },
    MODERATE_DROP: {
      title: "Notable volume drop",
      bgClass: "bg-[#F8FAFC]",
      borderClass: "border-[#94A3B8]",
      textClass: "text-[#334155]",
      icon: <TrendingDown className="w-5 h-5 text-[#64748B]" aria-hidden="true" />,
      badgeText: "Notable drop",
    },
    UNUSUAL_DROP: {
      title: "Unusual volume drop",
      bgClass: "bg-[#F1F5F9]",
      borderClass: "border-[#64748B]",
      textClass: "text-[#1E293B]",
      icon: <TrendingDown className="w-5 h-5 text-[#475569]" aria-hidden="true" />,
      badgeText: "Unusual drop",
    },
  };

  const config = severityConfig[data.severity] || severityConfig.NORMAL;
  const isSurge = data.deviation_pct > 0;

  return (
    <article
      aria-label="Emergency department arrival anomaly status"
      className="bg-white border border-[#D5DFDB] rounded p-5 sm:p-6 flex flex-col justify-between h-full"
    >
      <div>
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2.5 sm:gap-3">
          <div>
            <h2 className="font-heading text-base sm:text-lg font-bold text-[#122B32]">
              Arrival pattern status
            </h2>
            <p className="text-xs text-[#4A6369] mt-0.5">
              Compared against historical hour-of-week baseline
            </p>
          </div>

          {/* Severity Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold border w-fit ${config.bgClass} ${config.borderClass} ${config.textClass}`}
          >
            {config.icon}
            <span>{config.badgeText}</span>
          </div>
        </div>

        {/* Primary Deviation Metric */}
        <div className="mt-4">
          <div className="flex items-baseline gap-2">
            <span className="font-heading text-3xl sm:text-5xl font-extrabold text-[#122B32] tabular-numbers">
              {isSurge ? `+${data.deviation_pct.toFixed(1)}%` : `${data.deviation_pct.toFixed(1)}%`}
            </span>
            <span className="text-xs text-[#4A6369] font-medium">deviation</span>
          </div>
          <p className="text-xs text-[#4A6369] mt-1">
            Observed: <strong className="text-[#122B32] tabular-numbers">{data.observed_value}</strong> arrivals · Expected baseline: <strong className="text-[#122B32] tabular-numbers">{data.expected_baseline.toFixed(1)}</strong>
          </p>
        </div>
      </div>

      {/* Human-Readable Clinical Explanation & Alert Log Trigger */}
      <div className="mt-6 pt-4 border-t border-[#D5DFDB] space-y-3">
        <div className="p-3 bg-[#F3F6F4] border border-[#D5DFDB] rounded">
          <p className="text-xs leading-relaxed text-[#122B32]">
            {data.explanation}
          </p>
        </div>

        {onOpenAlertLog && (
          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-[#4A6369]">
              {unresolvedAlertsCount != null && unresolvedAlertsCount > 0 ? (
                <span className="text-[#B91C1C] font-semibold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#B91C1C] animate-pulse" />
                  {unresolvedAlertsCount} active alert{unresolvedAlertsCount === 1 ? "" : "s"}
                </span>
              ) : (
                "Alert history audit active"
              )}
            </span>
            <button
              type="button"
              onClick={onOpenAlertLog}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-[#F3F6F4] hover:bg-[#E5ECE9] text-[#122B32] border border-[#D5DFDB] transition-colors cursor-pointer"
            >
              <Bell className="w-3.5 h-3.5 text-[#0A6E73]" />
              <span>Alert History</span>
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
