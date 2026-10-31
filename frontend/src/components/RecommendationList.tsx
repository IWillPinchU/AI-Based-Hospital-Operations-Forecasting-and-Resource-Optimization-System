import React from "react";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  UserPlus,
  Bed,
  Check,
} from "lucide-react";
import { RecommendationResponse, RecommendationItem } from "@/lib/types";
import { formatCategoryName } from "@/lib/formatters";

interface RecommendationListProps {
  data: RecommendationResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function RecommendationList({
  data,
  isLoading,
  error,
}: RecommendationListProps) {
  if (isLoading) {
    return (
      <div className="bg-white border border-[#D5DFDB] rounded p-6 text-center text-sm text-[#4A6369]">
        Evaluating staffing and bed optimization rules...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-white border border-[#D5DFDB] rounded p-6 text-center text-sm text-[#B91C1C]">
        {error || "Optimization recommendations unavailable. Upload operational data to trigger rules."}
      </div>
    );
  }

  const recommendations = data.recommendations || [];
  const resourceState = data.resource_state;

  return (
    <section
      aria-label="Recommended operational adjustments"
      className="bg-white border border-[#D5DFDB] rounded p-5 sm:p-6"
    >
      {/* Header and Status Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#D5DFDB]">
        <div>
          <h2 className="font-heading text-lg sm:text-xl font-bold text-[#122B32]">
            Recommended operational adjustments
          </h2>
          <p className="text-xs text-[#4A6369] mt-0.5">
            {data.status_summary}
          </p>
        </div>

        {/* Resource State Summary Metrics */}
        {resourceState && (
          <div className="flex items-center gap-4 text-xs bg-[#F3F6F4] px-3.5 py-2 rounded border border-[#D5DFDB] shrink-0">
            <div>
              <span className="text-[#4A6369]">Projected load:</span>{" "}
              <strong className="text-[#122B32] tabular-numbers font-semibold">
                {resourceState.projected_ed_patients}
              </strong>
            </div>
            <div className="w-px h-4 bg-[#D5DFDB]" aria-hidden="true" />
            <div>
              <span className="text-[#4A6369]">Target nurses:</span>{" "}
              <strong className="text-[#122B32] tabular-numbers font-semibold">
                {resourceState.target_nurses_needed}
              </strong>
            </div>
            <div className="w-px h-4 bg-[#D5DFDB]" aria-hidden="true" />
            <div>
              <span className="text-[#4A6369]">Deficit:</span>{" "}
              <strong
                className={`tabular-numbers font-bold ${
                  resourceState.nurse_deficit > 0 ? "text-[#92400E]" : "text-[#2B8A3E]"
                }`}
              >
                {resourceState.nurse_deficit > 0 ? `+${resourceState.nurse_deficit}` : "0"}
              </strong>
            </div>
          </div>
        )}
      </div>

      {/* Action Queue List */}
      <div className="mt-5 space-y-4">
        {recommendations.length === 0 ? (
          <div className="p-6 bg-[#F0FDF4] border border-[#4ADE80] rounded flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-[#2B8A3E] shrink-0" aria-hidden="true" />
            <div>
              <p className="text-sm font-bold text-[#166534]">
                Operational capacity and staffing within acceptable limits
              </p>
              <p className="text-xs text-[#166534]/80 mt-0.5">
                No acute staffing deficit or inpatient bed turnover review required at current load.
              </p>
            </div>
          </div>
        ) : (
          recommendations.map((rec: RecommendationItem) => {
            const isStaffing = rec.category.toUpperCase().includes("STAFF");
            const isBed = rec.category.toUpperCase().includes("BED");

            return (
              <div
                key={rec.id}
                className="p-4 sm:p-5 rounded border border-[#D5DFDB] bg-[#FDFEFE] hover:bg-white transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div
                      className={`p-2 rounded shrink-0 mt-0.5 ${
                        isStaffing
                          ? "bg-[#FFFBEB] text-[#D9730D] border border-[#D9730D]/30"
                          : "bg-[#FFF5F5] text-[#C92A2A] border border-[#F87171]/40"
                      }`}
                    >
                      {isStaffing ? (
                        <UserPlus className="w-4 h-4" aria-hidden="true" />
                      ) : isBed ? (
                        <Bed className="w-4 h-4" aria-hidden="true" />
                      ) : (
                        <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#0A6E73] bg-[#0A6E73]/10 px-2 py-0.5 rounded">
                          {formatCategoryName(rec.category)}
                        </span>
                        <span className="text-xs font-semibold text-[#92400E] bg-[#FFFBEB] px-2 py-0.5 rounded border border-[#D9730D]/30">
                          {rec.priority.toLowerCase()} priority
                        </span>
                        <span className="text-[11px] text-[#4A6369] font-mono">
                          {rec.id}
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-[#122B32] mt-1.5">
                        {rec.action}
                      </h3>

                      <p className="text-xs text-[#122B32] mt-1 leading-relaxed">
                        <strong>Rationale:</strong> {rec.rationale}
                      </p>

                      {rec.constraints_checked && (
                        <div className="flex items-center gap-1.5 text-xs text-[#4A6369] mt-2 bg-[#F3F6F4] px-2.5 py-1 rounded border border-[#D5DFDB] w-fit">
                          <Check className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
                          <span>{rec.constraints_checked}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-right sm:shrink-0 text-[11px] text-[#4A6369] flex items-center sm:flex-col sm:items-end gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
                    <span>Supervisor verification required</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
