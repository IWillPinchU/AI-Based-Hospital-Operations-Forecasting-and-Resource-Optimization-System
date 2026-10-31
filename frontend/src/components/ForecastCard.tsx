"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus, Clock, AlertTriangle } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceDot,
} from "recharts";
import { ForecastResponse } from "@/lib/types";
import { formatUtcDateTime, formatUtcTime } from "@/lib/formatters";

interface ForecastCardProps {
  data: ForecastResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function ForecastCard({ data, isLoading, error }: ForecastCardProps) {
  if (isLoading) {
    return (
      <div className="bg-white border border-[#D5DFDB] rounded p-6 h-full flex items-center justify-center text-sm text-[#4A6369]">
        Calculating next-hour predictive forecast...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-white border border-[#D5DFDB] rounded p-6 h-full flex flex-col items-center justify-center text-center">
        <AlertTriangle className="w-8 h-8 text-[#D9730D] mb-2" aria-hidden="true" />
        <h3 className="font-heading text-base font-bold text-[#122B32]">
          Forecast unavailable
        </h3>
        <p className="text-xs text-[#4A6369] mt-1 max-w-sm">
          {error || "Upload at least 25 hours of operational data to supply lag features."}
        </p>
      </div>
    );
  }

  // Build chart points: 24 observed points + 1 forecasted point
  const chartPoints = (data.recent_arrivals || []).map((pt, idx) => ({
    time: formatUtcTime(pt.timestamp),
    rawTime: pt.timestamp,
    observed: pt.arrivals,
    forecast: null as number | null,
    isForecast: false,
    label: `Hour -${23 - idx}`,
  }));

  // Append next hour forecast point connected from latest observed
  const lastObserved = chartPoints[chartPoints.length - 1];
  if (lastObserved) {
    // Duplicate latest observed as start of dashed forecast line
    lastObserved.forecast = lastObserved.observed;
  }

  chartPoints.push({
    time: formatUtcTime(data.target_timestamp),
    rawTime: data.target_timestamp,
    observed: null as any,
    forecast: data.predicted_ed_arrivals,
    isForecast: true,
    label: "Next hour (projected)",
  });

  const netChange = data.expected_net_change;
  const isSurge = netChange > 0;
  const isDrop = netChange < 0;

  return (
    <article
      aria-label="Next-hour emergency department arrival forecast"
      className="bg-white border border-[#D5DFDB] rounded p-5 sm:p-6 flex flex-col justify-between h-full"
    >
      {/* Card Header */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-heading text-base sm:text-lg font-bold text-[#122B32]">
              Next-hour arrival forecast
            </h2>
            <div className="flex items-center gap-1.5 text-xs text-[#4A6369] mt-0.5">
              <Clock className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
              <span>Target: {formatUtcDateTime(data.target_timestamp)}</span>
            </div>
          </div>

          {/* Model Specification Note (no class name, no MAE) */}
          <span className="text-[11px] font-medium px-2.5 py-1 bg-[#F3F6F4] text-[#4A6369] rounded border border-[#D5DFDB]">
            Gradient boosting model
          </span>
        </div>

        {/* Primary Metric & Delta */}
        <div className="mt-4 flex flex-wrap items-baseline gap-3">
          <div className="flex items-baseline">
            <span className="font-heading text-4xl sm:text-5xl font-extrabold text-[#122B32] tabular-numbers">
              {data.predicted_ed_arrivals.toFixed(1)}
            </span>
            <span className="text-sm font-semibold text-[#4A6369] ml-2">expected arrivals</span>
          </div>

          <div
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold ${
              isSurge
                ? "bg-[#FFFBEB] text-[#92400E] border border-[#D9730D]/40"
                : isDrop
                ? "bg-[#F8FAFC] text-[#334155] border border-[#94A3B8]/40"
                : "bg-[#F3F6F4] text-[#4A6369] border border-[#D5DFDB]"
            }`}
          >
            {isSurge ? (
              <TrendingUp className="w-3.5 h-3.5 text-[#D9730D]" aria-hidden="true" />
            ) : isDrop ? (
              <TrendingDown className="w-3.5 h-3.5 text-[#64748B]" aria-hidden="true" />
            ) : (
              <Minus className="w-3.5 h-3.5 text-[#4A6369]" aria-hidden="true" />
            )}
            <span>
              {isSurge ? `+${netChange.toFixed(1)}` : `${netChange.toFixed(1)}`} from current ({data.current_ed_arrivals})
            </span>
          </div>
        </div>
      </div>

      {/* 24-Hour Observed Trajectory + Forecast Chart */}
      <div className="mt-6 pt-4 border-t border-[#D5DFDB]">
        <div className="flex items-center justify-between text-xs text-[#4A6369] mb-3">
          <span>24-hour historical trajectory and next-hour projection</span>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-[#0A6E73] inline-block" />
              <span>Observed</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 border-t border-dashed border-[#0A6E73] inline-block" />
              <span className="font-medium text-[#122B32]">Forecast</span>
            </div>
          </div>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartPoints}
              margin={{ top: 8, right: 12, left: -24, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E2EBE7" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 10, fill: "#4A6369" }}
                tickLine={false}
                axisLine={{ stroke: "#D5DFDB" }}
                interval={5}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#4A6369" }}
                tickLine={false}
                axisLine={false}
                domain={["auto", "auto"]}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const pt = payload[0].payload;
                    const val = pt.isForecast ? pt.forecast : pt.observed;
                    return (
                      <div className="bg-white border border-[#D5DFDB] p-2 rounded shadow-sm text-xs">
                        <p className="font-bold text-[#122B32]">{pt.time}</p>
                        <p className="text-[#4A6369]">
                          {pt.isForecast ? "Projected" : "Observed"}:{" "}
                          <strong className="text-[#122B32] tabular-numbers">{val}</strong> arrivals
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {/* Solid line for historical observed */}
              <Line
                type="monotone"
                dataKey="observed"
                stroke="#0A6E73"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              {/* Dashed line connecting latest observed to next hour forecast point */}
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="#0A6E73"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 4, fill: "#0A6E73", strokeWidth: 0 }}
                isAnimationActive={false}
              />
              {/* Accent dot on forecast */}
              <ReferenceDot
                x={formatUtcTime(data.target_timestamp)}
                y={data.predicted_ed_arrivals}
                r={5}
                fill="#0A6E73"
                stroke="#FFFFFF"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </article>
  );
}
