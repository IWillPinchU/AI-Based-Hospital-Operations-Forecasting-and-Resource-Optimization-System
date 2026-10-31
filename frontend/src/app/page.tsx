"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Upload, RefreshCw, AlertCircle } from "lucide-react";
import {
  fetchCurrentState,
  fetchForecast,
  fetchAnomalies,
  fetchRecommendations,
} from "@/lib/api";
import {
  CurrentStateResponse,
  ForecastResponse,
  AnomalyResponse,
  RecommendationResponse,
} from "@/lib/types";
import { Navbar } from "@/components/Navbar";
import { IngestionModal } from "@/components/IngestionModal";
import { CurrentStateStrip } from "@/components/CurrentStateStrip";
import { ForecastCard } from "@/components/ForecastCard";
import { AnomalySign } from "@/components/AnomalySign";
import { RecommendationList } from "@/components/RecommendationList";

export default function DashboardPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  // Layer 4 Recommendations
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(true);
  const [errorRecommendations, setErrorRecommendations] = useState<string | null>(null);

  // Fetch all endpoints independently for isolated resilience
  const refreshDashboard = useCallback(async () => {
    setIsRefreshing(true);

    // 1. Current State
    setLoadingState(true);
    fetchCurrentState()
      .then((data) => {
        setCurrentState(data);
        setErrorState(null);
      })
      .catch((err) => {
        setCurrentState(null);
        setErrorState(err.message || "Failed to load current state.");
      })
      .finally(() => setLoadingState(false));

    // 2. Forecast
    setLoadingForecast(true);
    fetchForecast()
      .then((data) => {
        setForecast(data);
        setErrorForecast(null);
      })
      .catch((err) => {
        setForecast(null);
        setErrorForecast(err.message || "Failed to load arrival forecast.");
      })
      .finally(() => setLoadingForecast(false));

    // 3. Anomalies
    setLoadingAnomaly(true);
    fetchAnomalies()
      .then((data) => {
        setAnomaly(data);
        setErrorAnomaly(null);
      })
      .catch((err) => {
        setAnomaly(null);
        setErrorAnomaly(err.message || "Failed to load anomaly detection.");
      })
      .finally(() => setLoadingAnomaly(false));

    // 4. Recommendations
    setLoadingRecommendations(true);
    fetchRecommendations()
      .then((data) => {
        setRecommendations(data);
        setErrorRecommendations(null);
      })
      .catch((err) => {
        setRecommendations(null);
        setErrorRecommendations(err.message || "Failed to load recommendations.");
      })
      .finally(() => {
        setLoadingRecommendations(false);
        setIsRefreshing(false);
      });
  }, []);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  const isEmptyDatabase = !loadingState && !currentState && errorState?.includes("404");

  return (
    <div className="min-h-screen flex flex-col bg-[#F3F6F4]">
      {/* Top Navbar */}
      <Navbar
        latestTimestamp={currentState?.timestamp}
        onOpenUpload={() => setIsModalOpen(true)}
      />

      {/* Main Dashboard Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full space-y-6">
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
                />
              </div>

              {/* Right: Anomaly Wayfinding Sign (5 cols on desktop ~40%) */}
              <div className="lg:col-span-5">
                <AnomalySign
                  data={anomaly}
                  isLoading={loadingAnomaly}
                  error={errorAnomaly}
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
          refreshDashboard();
        }}
      />
    </div>
  );
}
