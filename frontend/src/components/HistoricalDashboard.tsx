"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Calendar,
  Download,
  TrendingUp,
  Activity,
  Users,
  Bed,
  AlertTriangle,
  RefreshCw,
  Table as TableIcon,
  BarChart3,
  Sliders,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
  ReferenceLine,
} from "recharts";
import { fetchHistory } from "@/lib/api";
import { HistoricalResponse, HistoricalRecord } from "@/lib/types";
import { formatUtcDateTime, formatShortDate } from "@/lib/formatters";

type RangePreset = "24h" | "3d" | "7d" | "14d" | "30d" | "all" | "custom";
type MetricStream = "arrivals" | "beds_icu" | "staffing";
type ViewMode = "chart" | "table";

interface HistoricalDashboardProps {
  onRefreshTrigger?: () => void;
}

export function HistoricalDashboard({}: HistoricalDashboardProps) {
  const [preset, setPreset] = useState<RangePreset>("7d");
  const [stream, setStream] = useState<MetricStream>("arrivals");
  const [viewMode, setViewMode] = useState<ViewMode>("chart");
  const [showMovingAverage, setShowMovingAverage] = useState(true);

  // Custom date picker range
  const [customStart, setCustomStart] = useState<string>("");
  const [customEnd, setCustomEnd] = useState<string>("");

  // Data fetching state
  const [historyData, setHistoryData] = useState<HistoricalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Brush active scrub range state
  const [userBrushRange, setUserBrushRange] = useState<{ start: number; end: number } | null>(null);

  const loadData = useCallback(async (selectedPreset: RangePreset, startStr?: string, endStr?: string) => {
    setLoading(true);
    setError(null);
    setUserBrushRange(null);

    let startIso: string | undefined = undefined;
    let endIso: string | undefined = undefined;
    let limit = 720;

    const now = new Date();

    if (selectedPreset === "24h") {
      const d = new Date(now.getTime() - 24 * 3600 * 1000);
      startIso = d.toISOString();
      limit = 48;
    } else if (selectedPreset === "3d") {
      const d = new Date(now.getTime() - 3 * 24 * 3600 * 1000);
      startIso = d.toISOString();
      limit = 96;
    } else if (selectedPreset === "7d") {
      const d = new Date(now.getTime() - 7 * 24 * 3600 * 1000);
      startIso = d.toISOString();
      limit = 200;
    } else if (selectedPreset === "14d") {
      const d = new Date(now.getTime() - 14 * 24 * 3600 * 1000);
      startIso = d.toISOString();
      limit = 400;
    } else if (selectedPreset === "30d") {
      const d = new Date(now.getTime() - 30 * 24 * 3600 * 1000);
      startIso = d.toISOString();
      limit = 800;
    } else if (selectedPreset === "all") {
      limit = 2000;
    } else if (selectedPreset === "custom") {
      // Treat custom input datetime as UTC to match hospital database metrics
      if (startStr) {
        startIso = startStr.includes("Z") ? startStr : `${startStr}:00Z`;
      }
      if (endStr) {
        endIso = endStr.includes("Z") ? endStr : `${endStr}:00Z`;
      }
      limit = 2000;
    }

    try {
      const res = await fetchHistory({
        start: startIso,
        end: endIso,
        limit,
      });
      setHistoryData(res);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to load historical operations data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (preset !== "custom") {
      const timer = setTimeout(() => {
        loadData(preset);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [preset, loadData]);

  const handleApplyCustom = () => {
    if (preset === "custom") {
      loadData("custom", customStart, customEnd);
    }
  };

  // Process data for charts including 24-point rolling average
  const chartData = useMemo(() => {
    if (!historyData?.records || historyData.records.length === 0) return [];
    return historyData.records.map((r, i, arr) => {
      const windowStart = Math.max(0, i - 23);
      const slice = arr.slice(windowStart, i + 1);
      const movingAvg =
        slice.reduce((acc, c) => acc + c.ed_arrivals, 0) / slice.length;

      return {
        ...r,
        formattedTime: formatShortDate(r.timestamp),
        fullTime: formatUtcDateTime(r.timestamp),
        moving_avg_arrivals: Math.round(movingAvg * 10) / 10,
      };
    });
  }, [historyData]);

  const activeBrushRange = useMemo(() => {
    if (userBrushRange) return userBrushRange;
    if (chartData.length > 0) return { start: 0, end: chartData.length - 1 };
    return null;
  }, [userBrushRange, chartData.length]);

  const scrubbedStart = useMemo(() => {
    if (!chartData.length || !activeBrushRange) return "";
    const idx = Math.min(Math.max(0, activeBrushRange.start), chartData.length - 1);
    return chartData[idx]?.fullTime || "";
  }, [chartData, activeBrushRange]);

  const scrubbedEnd = useMemo(() => {
    if (!chartData.length || !activeBrushRange) return "";
    const idx = Math.min(Math.max(0, activeBrushRange.end), chartData.length - 1);
    return chartData[idx]?.fullTime || "";
  }, [chartData, activeBrushRange]);

  const scrubbedCount = useMemo(() => {
    if (!activeBrushRange) return 0;
    return Math.max(1, activeBrushRange.end - activeBrushRange.start + 1);
  }, [activeBrushRange]);

  // Export filtered CSV in browser
  const handleExportCsv = () => {
    if (!historyData?.records || historyData.records.length === 0) return;
    const headers = [
      "timestamp_utc",
      "ed_arrivals",
      "ed_patients",
      "available_beds",
      "icu_occupancy_pct",
      "nurses_available",
      "doctors_available",
    ];

    const rows = historyData.records.map((r) => [
      r.timestamp,
      r.ed_arrivals,
      r.ed_patients,
      r.available_beds,
      r.icu_occupancy_pct,
      r.nurses_available,
      r.doctors_available,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `hospital_operations_history_${preset}_${Date.now()}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const summary = historyData?.summary;

  return (
    <div className="space-y-6">
      {/* Top Filter and View Controller Bar */}
      <div className="bg-white border border-[#D5DFDB] rounded p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Range Selection Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-[#4A6369] uppercase tracking-wider flex items-center gap-1.5 mr-1">
            <Calendar className="w-3.5 h-3.5 text-[#0A6E73]" />
            Time Range:
          </span>
          {(
            [
              { id: "24h", label: "24 Hours" },
              { id: "3d", label: "3 Days" },
              { id: "7d", label: "7 Days" },
              { id: "14d", label: "14 Days" },
              { id: "30d", label: "30 Days" },
              { id: "all", label: "All Data" },
              { id: "custom", label: "Custom" },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setPreset(item.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                preset === item.id
                  ? "bg-[#0A6E73] text-white"
                  : "bg-[#F3F6F4] text-[#122B32] hover:bg-[#E5ECE9]"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Right: Actions (Refresh, Export, View Mode) */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {/* View Mode Toggle */}
          <div className="inline-flex rounded border border-[#D5DFDB] p-0.5 bg-[#F3F6F4]">
            <button
              type="button"
              onClick={() => setViewMode("chart")}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                viewMode === "chart"
                  ? "bg-white text-[#122B32] shadow-xs"
                  : "text-[#4A6369] hover:text-[#122B32]"
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Chart</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer ${
                viewMode === "table"
                  ? "bg-white text-[#122B32] shadow-xs"
                  : "text-[#4A6369] hover:text-[#122B32]"
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
          </div>

          {/* Export Button */}
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={!historyData?.records?.length}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-white border border-[#D5DFDB] text-[#122B32] hover:bg-[#F3F6F4] transition-colors cursor-pointer disabled:opacity-50"
            title="Download currently filtered records as CSV"
          >
            <Download className="w-3.5 h-3.5 text-[#0A6E73]" />
            <span>Export CSV</span>
          </button>

          {/* Manual Refresh */}
          <button
            type="button"
            onClick={() => loadData(preset, customStart, customEnd)}
            disabled={loading}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded bg-white border border-[#D5DFDB] text-[#122B32] hover:bg-[#F3F6F4] transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh history query"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#0A6E73] ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Custom Date Pickers (Shown only when preset === 'custom') */}
      {preset === "custom" && (
        <div className="bg-white border border-[#D5DFDB] rounded p-4 flex flex-col gap-3">
          <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-3 sm:gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2">
              <label htmlFor="custom-start" className="text-xs font-semibold text-[#4A6369]">
                Start Date/Time (UTC):
              </label>
              <input
                id="custom-start"
                type="datetime-local"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="text-xs border border-[#D5DFDB] rounded px-2.5 py-1.5 text-[#122B32] w-full sm:w-auto"
              />
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2">
              <label htmlFor="custom-end" className="text-xs font-semibold text-[#4A6369]">
                End Date/Time (UTC):
              </label>
              <input
                id="custom-end"
                type="datetime-local"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="text-xs border border-[#D5DFDB] rounded px-2.5 py-1.5 text-[#122B32] w-full sm:w-auto"
              />
            </div>
            <button
              type="button"
              onClick={handleApplyCustom}
              disabled={Boolean(customStart && customEnd && customStart > customEnd)}
              className="px-3.5 py-1.5 text-xs font-semibold rounded bg-[#0A6E73] text-white hover:bg-[#08565A] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed self-start sm:self-auto"
            >
              Apply Filter
            </button>
            <span className="text-[11px] text-[#0A6E73] font-medium w-full sm:w-auto">
              💡 All telemetry timestamps in this system are stored and evaluated in UTC.
            </span>
          </div>

          {(customStart || customEnd) && (
            <div className="flex items-center gap-2 text-xs pt-2 border-t border-[#F3F6F4]">
              <span className="text-[#4A6369]">Filter target window:</span>
              <span className="font-mono text-[11px] font-semibold text-[#122B32] bg-[#F3F6F4] px-2.5 py-1 rounded border border-[#D5DFDB]">
                {customStart ? `${customStart.replace("T", " ")}:00 UTC` : "Earliest"} →{" "}
                {customEnd ? `${customEnd.replace("T", " ")}:00 UTC` : "Latest"}
              </span>
              {customStart && customEnd && customStart > customEnd && (
                <span className="text-[#B91C1C] text-[11px] font-medium">
                  ⚠️ Start date/time must be earlier than end date/time.
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-white border border-[#D5DFDB] rounded p-4 text-sm text-[#B91C1C] flex items-center justify-center gap-2">
          <AlertTriangle className="w-4 h-4 text-[#C92A2A]" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="bg-white border border-[#D5DFDB] rounded p-8 text-center text-sm text-[#4A6369]">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0A6E73]" />
          Loading historical operations telemetry...
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && (!historyData?.records || historyData.records.length === 0) && (
        <div className="bg-white border border-[#D5DFDB] rounded p-12 text-center text-[#4A6369]">
          <Activity className="w-8 h-8 text-[#0A6E73]/50 mx-auto mb-3" />
          <h3 className="font-heading text-base font-bold text-[#122B32]">
            No historical records found
          </h3>
          <p className="text-xs text-[#4A6369] mt-1">
            No telemetry data matches the selected time range. Try selecting a broader range or uploading data.
          </p>
        </div>
      )}

      {/* Content when records exist */}
      {!loading && !error && summary && historyData?.records && historyData.records.length > 0 && (
        <>
          {/* Section 1: Period Aggregate Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Metric 1: Total Arrivals & Hourly Average */}
            <div className="bg-white border border-[#D5DFDB] rounded p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-xs text-[#4A6369]">
                <span>Total ED Arrivals</span>
                <TrendingUp className="w-4 h-4 text-[#0A6E73]" />
              </div>
              <div className="mt-2">
                <span className="font-heading text-2xl font-bold text-[#122B32]">
                  {summary.ed_arrivals.total?.toLocaleString() ?? summary.ed_arrivals.max}
                </span>
                <span className="text-xs text-[#4A6369] ml-1.5">arrivals</span>
              </div>
              <div className="text-xs text-[#4A6369] mt-2 pt-2 border-t border-[#F3F6F4] flex items-center justify-between">
                <span>Avg / hr:</span>
                <span className="font-semibold text-[#122B32]">
                  {summary.ed_arrivals.avg}
                </span>
              </div>
            </div>

            {/* Metric 2: Peak Surge Event */}
            <div className="bg-white border border-[#D5DFDB] rounded p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-xs text-[#4A6369]">
                <span>Peak Inflow Surge</span>
                <Activity className="w-4 h-4 text-[#C92A2A]" />
              </div>
              <div className="mt-2">
                <span className="font-heading text-2xl font-bold text-[#C92A2A]">
                  {summary.peak_arrivals}
                </span>
                <span className="text-xs text-[#4A6369] ml-1.5">arrivals/hr</span>
              </div>
              <div className="text-xs text-[#4A6369] mt-2 pt-2 border-t border-[#F3F6F4] truncate">
                <span>Peak: </span>
                <span className="font-medium text-[#122B32]">
                  {formatShortDate(summary.peak_arrival_timestamp)}
                </span>
              </div>
            </div>

            {/* Metric 3: Inpatient Bed Availability */}
            <div className="bg-white border border-[#D5DFDB] rounded p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-xs text-[#4A6369]">
                <span>Inpatient Bed Capacity</span>
                <Bed className="w-4 h-4 text-[#0A6E73]" />
              </div>
              <div className="mt-2">
                <span className="font-heading text-2xl font-bold text-[#122B32]">
                  {summary.available_beds.avg}
                </span>
                <span className="text-xs text-[#4A6369] ml-1.5">avg beds</span>
              </div>
              <div className="text-xs text-[#4A6369] mt-2 pt-2 border-t border-[#F3F6F4] flex items-center justify-between">
                <span>Critical min:</span>
                <span className="font-semibold text-[#122B32]">
                  {summary.available_beds.min} beds
                </span>
              </div>
            </div>

            {/* Metric 4: ICU Occupancy Rate */}
            <div className="bg-white border border-[#D5DFDB] rounded p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-xs text-[#4A6369]">
                <span>ICU Occupancy</span>
                <Users className="w-4 h-4 text-[#2563EB]" />
              </div>
              <div className="mt-2">
                <span
                  className={`font-heading text-2xl font-bold ${
                    summary.icu_occupancy_pct.max >= 85 ? "text-[#C92A2A]" : "text-[#122B32]"
                  }`}
                >
                  {summary.icu_occupancy_pct.avg}%
                </span>
                <span className="text-xs text-[#4A6369] ml-1.5">avg occupancy</span>
              </div>
              <div className="text-xs text-[#4A6369] mt-2 pt-2 border-t border-[#F3F6F4] flex items-center justify-between">
                <span>Period peak:</span>
                <span
                  className={`font-semibold ${
                    summary.icu_occupancy_pct.max >= 85 ? "text-[#C92A2A]" : "text-[#122B32]"
                  }`}
                >
                  {summary.icu_occupancy_pct.max}%
                </span>
              </div>
            </div>
          </div>

          {/* Section 2: Visual Chart or Data Table */}
          {viewMode === "chart" ? (
            <div className="bg-white border border-[#D5DFDB] rounded p-5 space-y-4">
              {/* Metric Stream Selector & Trend Overlay Toggle */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#D5DFDB] pb-3">
                {/* Metric Stream Switcher */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs font-semibold text-[#4A6369] mr-1">Stream:</span>
                  {(
                    [
                      { id: "arrivals", label: "ED Arrivals & Inflow" },
                      { id: "beds_icu", label: "Bed Capacity & ICU" },
                      { id: "staffing", label: "Staffing Telemetry" },
                    ] as const
                  ).map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setStream(m.id)}
                      className={`px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                        stream === m.id
                          ? "bg-[#122B32] text-white"
                          : "bg-[#F3F6F4] text-[#4A6369] hover:text-[#122B32]"
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>

                {/* 24-Hour Trend Overlay Toggle (for arrivals stream) */}
                {stream === "arrivals" && (
                  <label className="flex items-center gap-2 text-xs text-[#4A6369] cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={showMovingAverage}
                      onChange={(e) => setShowMovingAverage(e.target.checked)}
                      className="rounded border-[#D5DFDB] text-[#0A6E73] focus:ring-[#0A6E73]"
                    />
                    <Sliders className="w-3.5 h-3.5 text-[#D97706]" />
                    <span>Overlay 24h Moving Average</span>
                  </label>
                )}
              </div>

              {/* Chart Subheading & Instructions */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs text-[#4A6369]">
                <span>
                  Showing {chartData.length} hourly observation points ({formatShortDate(summary.start_timestamp)} — {formatShortDate(summary.end_timestamp)})
                </span>
                <span className="text-[11px] text-[#0A6E73] hidden md:inline">
                  💡 Tip: Drag handles on the bottom slider to zoom or scrub through time
                </span>
              </div>

              {/* Recharts Chart with Interactive Brush */}
              <div className="h-[380px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  {stream === "arrivals" ? (
                    <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5ECE9" />
                      <XAxis
                        dataKey="formattedTime"
                        tick={{ fontSize: 11, fill: "#4A6369" }}
                        tickLine={{ stroke: "#D5DFDB" }}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        width={45}
                        tick={{ fontSize: 11, fill: "#4A6369" }}
                        tickLine={{ stroke: "#D5DFDB" }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          border: "1px solid #D5DFDB",
                          borderRadius: "4px",
                          fontSize: "12px",
                        }}
                        labelFormatter={(_, payload) => {
                          if (payload && payload[0]) {
                            return (payload[0].payload as { fullTime?: string }).fullTime;
                          }
                          return "";
                        }}
                      />
                      <Legend verticalAlign="top" height={36} iconType="circle" />
                      <Line
                        type="monotone"
                        dataKey="ed_arrivals"
                        name="ED Arrivals"
                        stroke="#0A6E73"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 5 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="ed_patients"
                        name="Active ED Patients"
                        stroke="#2563EB"
                        strokeWidth={1.5}
                        dot={false}
                      />
                      {showMovingAverage && (
                        <Line
                          type="monotone"
                          dataKey="moving_avg_arrivals"
                          name="24h Trend (SMA)"
                          stroke="#D97706"
                          strokeWidth={2}
                          strokeDasharray="4 4"
                          dot={false}
                        />
                      )}
                      <Brush
                        dataKey="formattedTime"
                        height={28}
                        stroke="#0A6E73"
                        fill="#F3F6F4"
                        travellerWidth={10}
                        tickFormatter={() => ""}
                        onChange={(e) => {
                          if (e && typeof e.startIndex === "number" && typeof e.endIndex === "number") {
                            setUserBrushRange({ start: e.startIndex, end: e.endIndex });
                          }
                        }}
                      />
                    </LineChart>
                  ) : stream === "beds_icu" ? (
                    <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5ECE9" />
                      <XAxis
                        dataKey="formattedTime"
                        tick={{ fontSize: 11, fill: "#4A6369" }}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        yAxisId="left"
                        width={45}
                        tick={{ fontSize: 11, fill: "#0A6E73" }}
                        domain={["auto", "auto"]}
                      />
                      <YAxis
                        yAxisId="right"
                        width={45}
                        orientation="right"
                        tick={{ fontSize: 11, fill: "#C92A2A" }}
                        domain={[0, 100]}
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          border: "1px solid #D5DFDB",
                          borderRadius: "4px",
                          fontSize: "12px",
                        }}
                        labelFormatter={(_, payload) => {
                          if (payload && payload[0]) {
                            return (payload[0].payload as { fullTime?: string }).fullTime;
                          }
                          return "";
                        }}
                      />
                      <Legend verticalAlign="top" height={36} iconType="circle" />
                      <ReferenceLine
                        yAxisId="right"
                        y={85}
                        label={{ value: "Critical ICU (85%)", fill: "#C92A2A", fontSize: 10 }}
                        stroke="#C92A2A"
                        strokeDasharray="3 3"
                      />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="available_beds"
                        name="Available Beds"
                        stroke="#0A6E73"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="icu_occupancy_pct"
                        name="ICU Occupancy %"
                        stroke="#C92A2A"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Brush
                        dataKey="formattedTime"
                        height={28}
                        stroke="#0A6E73"
                        fill="#F3F6F4"
                        travellerWidth={10}
                        tickFormatter={() => ""}
                        onChange={(e) => {
                          if (e && typeof e.startIndex === "number" && typeof e.endIndex === "number") {
                            setUserBrushRange({ start: e.startIndex, end: e.endIndex });
                          }
                        }}
                      />
                    </LineChart>
                  ) : (
                    <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5ECE9" />
                      <XAxis
                        dataKey="formattedTime"
                        tick={{ fontSize: 11, fill: "#4A6369" }}
                        interval="preserveStartEnd"
                      />
                      <YAxis width={45} tick={{ fontSize: 11, fill: "#4A6369" }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          border: "1px solid #D5DFDB",
                          borderRadius: "4px",
                          fontSize: "12px",
                        }}
                        labelFormatter={(_, payload) => {
                          if (payload && payload[0]) {
                            return (payload[0].payload as { fullTime?: string }).fullTime;
                          }
                          return "";
                        }}
                      />
                      <Legend verticalAlign="top" height={36} iconType="circle" />
                      <Line
                        type="stepAfter"
                        dataKey="nurses_available"
                        name="Active Nurses on Duty"
                        stroke="#059669"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="stepAfter"
                        dataKey="doctors_available"
                        name="Active Doctors on Duty"
                        stroke="#7C3AED"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Brush
                        dataKey="formattedTime"
                        height={28}
                        stroke="#0A6E73"
                        fill="#F3F6F4"
                        travellerWidth={10}
                        tickFormatter={() => ""}
                        onChange={(e) => {
                          if (e && typeof e.startIndex === "number" && typeof e.endIndex === "number") {
                            setUserBrushRange({ start: e.startIndex, end: e.endIndex });
                          }
                        }}
                      />
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </div>

              {/* Dynamic Scrubbed Window Range Indicator */}
              {chartData.length > 2 && scrubbedStart && scrubbedEnd && (
                <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs px-3.5 py-2 bg-[#F3F6F4] rounded border border-[#D5DFDB] gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[#4A6369] font-medium">Scrubbed Window:</span>
                    <span className="font-semibold text-[#122B32]">{scrubbedStart}</span>
                    <span className="text-[#4A6369]">→</span>
                    <span className="font-semibold text-[#122B32]">{scrubbedEnd}</span>
                  </div>
                  <div className="text-[11px] text-[#0A6E73] font-medium flex items-center gap-1.5">
                    <span className="bg-white px-2 py-0.5 rounded border border-[#D5DFDB] text-[#122B32]">
                      {scrubbedCount} {scrubbedCount === 1 ? "hour" : "hours"} visible
                    </span>
                    <span className="hidden sm:inline">◀ Drag slider handles to zoom or scrub ▶</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Raw Telemetry Data Table */
            <div className="bg-white border border-[#D5DFDB] rounded overflow-hidden">
              <div className="p-3.5 sm:p-4 border-b border-[#D5DFDB] flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                <div>
                  <h4 className="font-heading text-sm font-bold text-[#122B32]">
                    Operational Telemetry Records
                  </h4>
                  <p className="text-xs text-[#4A6369]">
                    Showing all {historyData.records.length} records in selected range
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleExportCsv}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-[#0A6E73] text-white hover:bg-[#08565A] transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Table CSV</span>
                </button>
              </div>

              <div className="overflow-x-auto max-h-[420px]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#F3F6F4] text-[#4A6369] font-semibold border-b border-[#D5DFDB] sticky top-0">
                    <tr>
                      <th className="py-2.5 px-4">Timestamp (UTC)</th>
                      <th className="py-2.5 px-4 text-right">ED Arrivals</th>
                      <th className="py-2.5 px-4 text-right">ED Patients</th>
                      <th className="py-2.5 px-4 text-right">Available Beds</th>
                      <th className="py-2.5 px-4 text-right">ICU Occupancy</th>
                      <th className="py-2.5 px-4 text-right">Nurses</th>
                      <th className="py-2.5 px-4 text-right">Doctors</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D5DFDB] text-[#122B32]">
                    {historyData.records.map((row: HistoricalRecord, idx: number) => (
                      <tr key={idx} className="hover:bg-[#F3F6F4]/60 transition-colors">
                        <td className="py-2 px-4 font-mono text-[11px] text-[#4A6369]">
                          {formatUtcDateTime(row.timestamp)}
                        </td>
                        <td className="py-2 px-4 text-right font-medium">
                          {row.ed_arrivals}
                        </td>
                        <td className="py-2 px-4 text-right text-[#2563EB]">
                          {row.ed_patients}
                        </td>
                        <td className="py-2 px-4 text-right text-[#0A6E73]">
                          {row.available_beds}
                        </td>
                        <td className="py-2 px-4 text-right">
                          <span
                            className={
                              row.icu_occupancy_pct >= 85
                                ? "text-[#C92A2A] font-bold"
                                : ""
                            }
                          >
                            {row.icu_occupancy_pct}%
                          </span>
                        </td>
                        <td className="py-2 px-4 text-right text-[#059669]">
                          {row.nurses_available}
                        </td>
                        <td className="py-2 px-4 text-right text-[#7C3AED]">
                          {row.doctors_available}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
