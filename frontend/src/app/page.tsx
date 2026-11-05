"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Upload } from "lucide-react";
import {
  fetchCurrentState,
  fetchForecast,
  fetchAnomalies,
  fetchAnomalyHistory,
  fetchRecommendations,
  fetchModelBenchmarks,
} from "@/lib/api";
import {
  CurrentStateResponse,
  ForecastResponse,
  AnomalyResponse,
  RecommendationResponse,
  ModelBenchmarkItem,
} from "@/lib/types";
import { Navbar } from "@/components/Navbar";
import { IngestionModal } from "@/components/IngestionModal";
import { CurrentStateStrip } from "@/components/CurrentStateStrip";
import { ForecastCard } from "@/components/ForecastCard";
import { AnomalySign } from "@/components/AnomalySign";
import { RecommendationList } from "@/components/RecommendationList";
import { ModelBenchmarkModal } from "@/components/ModelBenchmarkModal";
import { HistoricalDashboard } from "@/components/HistoricalDashboard";
import { AnomalyAlertLogModal } from "@/components/AnomalyAlertLogModal";
import { ShiftReportModal } from "@/components/ShiftReportModal";
import { useTelemetryWebSocket } from "@/lib/useTelemetryWebSocket";

const POLL_INTERVAL_MS = 10000;

function isNetworkFailure(err: unknown): boolean {
  return typeof (err as { status?: unknown } | null)?.status !== "number";
}

export default function DashboardPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [livePaused, setLivePaused] = useState(false);
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");

  // Layer 1 State
  const [currentState, setCurrentState] = useState<CurrentStateResponse | null>(null);
  const [loadingState, setLoadingState] = useState(true);
  const [errorState, setErrorState] = useState<string | null>(null);

  // Layer 2 Forecast
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loadingForecast, setLoadingForecast] = useState(true);
  const [errorForecast, setErrorForecast] = useState<string | null>(null);

  // Layer 3 Anomaly
  const [anomaly, setAnomaly] = useState<AnomalyResponse | null>(null);
  const [loadingAnomaly, setLoadingAnomaly] = useState(true);
  const [errorAnomaly, setErrorAnomaly] = useState<string | null>(null);
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [unresolvedAlertsCount, setUnresolvedAlertsCount] = useState<number | undefined>(undefined);

  // Layer 4 Recommendations
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(true);
  const [errorRecommendations, setErrorRecommendations] = useState<string | null>(null);

  // Multi-Model Forecasting State
  const [selectedModel, setSelectedModel] = useState<string>("hist_gbr");
  const [isBenchmarkModalOpen, setIsBenchmarkModalOpen] = useState(false);
  const [benchmarkModels, setBenchmarkModels] = useState<ModelBenchmarkItem[]>([]);

  // Load benchmarks once on mount
  useEffect(() => {
    fetchModelBenchmarks()
      .then((res) => {
        if (res && res.models) setBenchmarkModels(res.models);
      })
      .catch(() => {});
  }, []);

  // Fetch all endpoints independently for isolated resilience
  const refreshDashboard = useCallback((showLoading: boolean) => {
    // Per-call tally so overlapping refreshes never share state.
    let settled = 0;
    let unreachable = false;
    const settle = (wasUnreachable: boolean) => {
      if (wasUnreachable) unreachable = true;
      settled += 1;
      if (settled < 4) return;
      if (unreachable) {
        setLivePaused(true);
      } else {
        setLivePaused(false);
        setLastRefreshedAt(new Date());
      }
    };

    // Layer request: on network failure during a poll, keep the card untouched.
    const run = <T,>(
      request: () => Promise<T>,
      onData: (data: T) => void,
      onError: (message: string) => void,
      setLoading: (v: boolean) => void,
      fallbackMessage: string
    ) => {
      if (showLoading) setLoading(true);
      request()
        .then((data) => {
          onData(data);
          settle(false);
        })
        .catch((err) => {
          const unreachableErr = isNetworkFailure(err);
          if (!(unreachableErr && !showLoading)) {
            onError(err?.message || fallbackMessage);
          }
          settle(unreachableErr);
        })
        .finally(() => {
          if (showLoading) setLoading(false);
        });
    };

    run(
      fetchCurrentState,
      (data) => {
        setCurrentState(data);
        setErrorState(null);
      },
      (message) => {
        setCurrentState(null);
        setErrorState(message);
      },
      setLoadingState,
      "Failed to load current state."
    );

    run(
      () => fetchForecast(selectedModel),
      (data) => {
        setForecast(data);
        setErrorForecast(null);
      },
      (message) => {
        setForecast(null);
        setErrorForecast(message);
      },
      setLoadingForecast,
      "Failed to load arrival forecast."
    );

    run(
      fetchAnomalies,
      (data) => {
        setAnomaly(data);
        setErrorAnomaly(null);
        fetchAnomalyHistory({ limit: 1 })
          .then((res) => {
            if (res && res.summary) {
              setUnresolvedAlertsCount(res.summary.unresolved_count);
            }
          })
          .catch(() => {});
      },
      (message) => {
        setAnomaly(null);
        setErrorAnomaly(message);
      },
      setLoadingAnomaly,
      "Failed to load anomaly detection."
    );

    run(
      fetchRecommendations,
      (data) => {
        setRecommendations(data);
        setErrorRecommendations(null);
      },
      (message) => {
        setRecommendations(null);
        setErrorRecommendations(message);
      },
      setLoadingRecommendations,
      "Failed to load recommendations."
    );
  }, [selectedModel]);

  // When model selection changes, re-fetch the forecast with that model
  const handleSelectModel = useCallback((modelId: string) => {
    setSelectedModel(modelId);
    setLoadingForecast(true);
    fetchForecast(modelId)
      .then((data) => {
        setForecast(data);
        setErrorForecast(null);
      })
      .catch((err) => {
        setErrorForecast(err?.message || "Failed to load forecast for selected model.");
      })
      .finally(() => {
        setLoadingForecast(false);
      });
  }, []);

  // Real-time WebSocket connection
  const handleWebSocketUpdate = useCallback(() => {
    // When backend broadcasts a new record or CSV ingestion, refresh instantly
    refreshDashboard(false);
  }, [refreshDashboard]);

  const { status: wsStatus } = useTelemetryWebSocket({
    onDataUpdated: handleWebSocketUpdate,
    enabled: true,
  });

  useEffect(() => {
    const id = setTimeout(() => refreshDashboard(true), 0);
    return () => clearTimeout(id);
  }, [refreshDashboard]);

  // Fallback background polling (every 30s when WebSocket is active, 10s if disconnected)
  useEffect(() => {
    const intervalMs = wsStatus === "connected" ? 30000 : POLL_INTERVAL_MS;
    const id = setInterval(() => refreshDashboard(false), intervalMs);
    return () => clearInterval(id);
  }, [refreshDashboard, wsStatus]);

  const isEmptyDatabase = !loadingState && !currentState && errorState?.includes("404");

  return (
    <div className="min-h-screen flex flex-col bg-[#F3F6F4]">
      {/* Top Navbar */}
      <Navbar
        latestTimestamp={currentState?.timestamp}
        onOpenUpload={() => setIsModalOpen(true)}
        onOpenShiftReport={() => setIsReportModalOpen(true)}
        lastRefreshedAt={lastRefreshedAt}
        livePaused={livePaused}
        wsStatus={wsStatus}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Main Dashboard Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full space-y-6">
        {/* Mobile Navigation Tabs */}
        <div className="flex lg:hidden items-center justify-center p-1 bg-white rounded border border-[#D5DFDB]">
          <button
            type="button"
            onClick={() => setActiveTab("live")}
            className={`flex-1 py-1.5 text-xs font-semibold rounded text-center transition-colors cursor-pointer ${
              activeTab === "live"
                ? "bg-[#0A6E73] text-white"
                : "text-[#4A6369] hover:text-[#122B32]"
            }`}
          >
            Live Monitor
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("history")}
            className={`flex-1 py-1.5 text-xs font-semibold rounded text-center transition-colors cursor-pointer ${
              activeTab === "history"
                ? "bg-[#0A6E73] text-white"
                : "text-[#4A6369] hover:text-[#122B32]"
            }`}
          >
            Historical Analytics
          </button>
        </div>

        {isEmptyDatabase ? (
          /* Empty State Inviting Upload */
          <div className="bg-white border border-[#D5DFDB] rounded p-12 text-center max-w-xl mx-auto my-12">
            <div className="w-12 h-12 rounded-full bg-[#0A6E73]/10 text-[#0A6E73] flex items-center justify-center mx-auto mb-4">
              <Upload className="w-6 h-6" aria-hidden="true" />
            </div>
            <h2 className="font-heading text-xl font-bold text-[#122B32]">
              No operational hospital data uploaded
            </h2>
            <p className="text-sm text-[#4A6369] mt-2 leading-relaxed">
              Upload a 7-column operational CSV file (or the generated synthetic hospital dataset) to initialize department vitals, next-hour forecasting, anomaly surveillance, and staffing optimization.
            </p>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-2 bg-[#0A6E73] hover:bg-[#08565A] text-white text-sm font-semibold px-4 py-2.5 rounded mt-6 transition-colors cursor-pointer"
            >
              <Upload className="w-4 h-4" aria-hidden="true" />
              <span>Upload operational CSV</span>
            </button>
          </div>
        ) : activeTab === "history" ? (
          /* Historical Analytics View */
          <HistoricalDashboard />
        ) : (
          <>
            {/* Section 1: Current State Vitals Telemetry */}
            <CurrentStateStrip
              data={currentState}
              recommendationsData={recommendations}
              isLoading={loadingState}
              error={errorState}
            />

            {/* Section 2: Predictive Intelligence (Two-Column Asymmetric Grid) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              {/* Hero Left: Next-Hour Forecast with Trajectory (7 cols on desktop ~60%) */}
              <div className="lg:col-span-7">
                <ForecastCard
                  data={forecast}
                  isLoading={loadingForecast}
                  error={errorForecast}
                  selectedModel={selectedModel}
                  onSelectModel={handleSelectModel}
                  onOpenBenchmarks={() => setIsBenchmarkModalOpen(true)}
                />
              </div>

              {/* Right: Anomaly Wayfinding Sign (5 cols on desktop ~40%) */}
              <div className="lg:col-span-5">
                <AnomalySign
                  data={anomaly}
                  isLoading={loadingAnomaly}
                  error={errorAnomaly}
                  onOpenAlertLog={() => setIsAlertModalOpen(true)}
                  unresolvedAlertsCount={unresolvedAlertsCount}
                />
              </div>
            </div>

            {/* Section 3: Prioritized Action Queue */}
            <RecommendationList
              data={recommendations}
              isLoading={loadingRecommendations}
              error={errorRecommendations}
            />
          </>
        )}
      </main>

      {/* CSV Ingestion Modal */}
      <IngestionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          refreshDashboard(true);
        }}
      />

      {/* Model Benchmark Leaderboard Modal */}
      <ModelBenchmarkModal
        isOpen={isBenchmarkModalOpen}
        onClose={() => setIsBenchmarkModalOpen(false)}
        models={benchmarkModels}
        selectedModel={selectedModel}
        onSelectModel={(id) => {
          handleSelectModel(id);
          setIsBenchmarkModalOpen(false);
        }}
      />

      {/* Anomaly History & Operational Alert Log Modal */}
      <AnomalyAlertLogModal
        isOpen={isAlertModalOpen}
        onClose={() => setIsAlertModalOpen(false)}
        onAlertUpdated={() => {
          fetchAnomalyHistory({ limit: 1 })
            .then((res) => {
              if (res && res.summary) setUnresolvedAlertsCount(res.summary.unresolved_count);
            })
            .catch(() => {});
        }}
      />

      {/* Shift Handover Report Modal */}
      <ShiftReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />
    </div>
  );
}
