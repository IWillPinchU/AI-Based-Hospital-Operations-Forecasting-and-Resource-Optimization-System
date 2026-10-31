import React from "react";
import { Users, Bed, Activity, UserCheck, AlertTriangle } from "lucide-react";
import { CurrentStateResponse, RecommendationResponse } from "@/lib/types";

interface CurrentStateStripProps {
  data: CurrentStateResponse | null;
  recommendationsData: RecommendationResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function CurrentStateStrip({
  data,
  recommendationsData,
  isLoading,
  error,
}: CurrentStateStripProps) {
  if (isLoading) {
    return (
      <section
        aria-label="Current hospital operations status"
        className="bg-white border border-[#D5DFDB] rounded p-4 text-center text-sm text-[#4A6369]"
      >
        Loading hospital vitals telemetry...
      </section>
    );
  }

  if (error || !data) {
    return (
      <section
        aria-label="Current hospital operations status"
        className="bg-white border border-[#D5DFDB] rounded p-4 text-sm text-[#B91C1C] flex items-center justify-center gap-2"
      >
        <AlertTriangle className="w-4 h-4 text-[#C92A2A]" aria-hidden="true" />
        <span>{error || "Current state unavailable. Please upload operational data."}</span>
      </section>
    );
  }

  // Derive alert states dynamically from recommendations payload (no hardcoded thresholds)
  const bedRecommendation = recommendationsData?.recommendations.find(
    (r) => r.category === "BED_MANAGEMENT"
  );
  const bedAlertActive =
    bedRecommendation?.rationale.toLowerCase().includes("available beds") ?? false;
  const icuAlertActive =
    bedRecommendation?.rationale.toLowerCase().includes("icu occupancy") ?? false;

  return (
    <section
      aria-label="Current hospital operations status"
      className="bg-white border border-[#D5DFDB] rounded overflow-hidden"
    >
      <div className="grid grid-cols-2 md:grid-cols-5 divide-y md:divide-y-0 md:divide-x divide-[#D5DFDB]">
        {/* Metric 1: ED Arrivals */}
        <div className="p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-[#4A6369]">
            <span>ED arrivals</span>
            <Activity className="w-4 h-4 text-[#0A6E73]" aria-hidden="true" />
          </div>
          <div className="mt-2">
            <span className="font-heading text-3xl font-bold text-[#122B32] tabular-numbers">
              {data.ed_arrivals}
            </span>
            <span className="text-xs text-[#4A6369] ml-1.5 font-medium">arrivals/hr</span>
          </div>
          <p className="text-xs text-[#4A6369] mt-1">Observed in current hour</p>
        </div>

        {/* Metric 2: Active ED Patients */}
        <div className="p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-[#4A6369]">
            <span>Active patients</span>
            <Users className="w-4 h-4 text-[#0A6E73]" aria-hidden="true" />
          </div>
          <div className="mt-2">
            <span className="font-heading text-3xl font-bold text-[#122B32] tabular-numbers">
              {data.ed_patients}
            </span>
            <span className="text-xs text-[#4A6369] ml-1.5 font-medium">in department</span>
          </div>
          <p className="text-xs text-[#4A6369] mt-1">Currently receiving care</p>
        </div>

        {/* Metric 3: Inpatient Beds */}
        <div
          className={`p-4 sm:p-5 flex flex-col justify-between ${
            bedAlertActive
              ? "bg-[#FFFBEB] border-l-2 border-l-[#D9730D]"
              : ""
          }`}
        >
          <div className="flex items-center justify-between text-xs">
            <span className={bedAlertActive ? "text-[#92400E] font-semibold" : "text-[#4A6369]"}>
              Inpatient beds
            </span>
            <Bed
              className={`w-4 h-4 ${
                bedAlertActive ? "text-[#D9730D]" : "text-[#0A6E73]"
              }`}
              aria-hidden="true"
            />
          </div>
          <div className="mt-2">
            <span
              className={`font-heading text-3xl font-bold tabular-numbers ${
                bedAlertActive ? "text-[#92400E]" : "text-[#122B32]"
              }`}
            >
              {data.available_beds}
            </span>
            <span
              className={`text-xs ml-1.5 font-medium ${
                bedAlertActive ? "text-[#92400E]" : "text-[#4A6369]"
              }`}
            >
              available
            </span>
          </div>
          <p className={`text-xs mt-1 ${bedAlertActive ? "text-[#92400E]" : "text-[#4A6369]"}`}>
            {bedAlertActive ? "Buffer review advised" : "Immediate bed capacity"}
          </p>
        </div>

        {/* Metric 4: ICU Occupancy */}
        <div
          className={`p-4 sm:p-5 flex flex-col justify-between ${
            icuAlertActive
              ? "bg-[#FFF5F5] border-l-2 border-l-[#F87171]"
              : ""
          }`}
        >
          <div className="flex items-center justify-between text-xs">
            <span className={icuAlertActive ? "text-[#B91C1C] font-semibold" : "text-[#4A6369]"}>
              ICU occupancy
            </span>
            <Activity
              className={`w-4 h-4 ${
                icuAlertActive ? "text-[#C92A2A]" : "text-[#0A6E73]"
              }`}
              aria-hidden="true"
            />
          </div>
          <div className="mt-2">
            <span
              className={`font-heading text-3xl font-bold tabular-numbers ${
                icuAlertActive ? "text-[#B91C1C]" : "text-[#122B32]"
              }`}
            >
              {data.icu_occupancy_pct.toFixed(1)}%
            </span>
          </div>
          <p className={`text-xs mt-1 ${icuAlertActive ? "text-[#B91C1C]" : "text-[#4A6369]"}`}>
            {icuAlertActive ? "Warning threshold reached" : "Critical care occupancy"}
          </p>
        </div>

        {/* Metric 5: Staff on Duty */}
        <div className="p-4 sm:p-5 flex flex-col justify-between col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-xs text-[#4A6369]">
            <span>Staff on duty</span>
            <UserCheck className="w-4 h-4 text-[#0A6E73]" aria-hidden="true" />
          </div>
          <div className="mt-2 flex items-baseline gap-3">
            <div>
              <span className="font-heading text-2xl font-bold text-[#122B32] tabular-numbers">
                {data.nurses_available}
              </span>
              <span className="text-xs text-[#4A6369] ml-1">nurses</span>
            </div>
            <div>
              <span className="font-heading text-2xl font-bold text-[#122B32] tabular-numbers">
                {data.doctors_available}
              </span>
              <span className="text-xs text-[#4A6369] ml-1">doctors</span>
            </div>
          </div>
          <p className="text-xs text-[#4A6369] mt-1">
            Ratios: {data.metrics.patient_to_nurse_ratio}:1 nurse · {data.metrics.patient_to_doctor_ratio}:1 doctor
          </p>
        </div>
      </div>
    </section>
  );
}
