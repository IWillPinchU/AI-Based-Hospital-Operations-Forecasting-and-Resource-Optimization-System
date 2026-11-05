"use client";

import React from "react";
import { X, Award, Cpu, CheckCircle } from "lucide-react";
import { ModelBenchmarkItem } from "@/lib/types";

interface ModelBenchmarkModalProps {
  isOpen: boolean;
  onClose: () => void;
  models: ModelBenchmarkItem[];
  selectedModel: string;
  onSelectModel: (modelId: string) => void;
}

export function ModelBenchmarkModal({
  isOpen,
  onClose,
  models,
  selectedModel,
  onSelectModel,
}: ModelBenchmarkModalProps) {
  if (!isOpen) return null;

  // Identify top performers
  const lowestMae = Math.min(...models.map((m) => m.mae));
  const lowestLatency = Math.min(...models.map((m) => m.latency_ms));

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="benchmark-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="bg-white rounded border border-[#D5DFDB] max-w-3xl w-full p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#D5DFDB]">
          <div>
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-[#0A6E73]" aria-hidden="true" />
              <h2 id="benchmark-title" className="font-heading text-lg font-bold text-[#122B32]">
                Comparative Model Evaluation Leaderboard
              </h2>
            </div>
            <p className="text-xs text-[#4A6369] mt-1">
              80/20 temporal train/test split (no future data leakage). Benchmarked on holdout arrivals.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#4A6369] hover:text-[#122B32] p-1 rounded transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Comparison Table */}
        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#D5DFDB] bg-[#F3F6F4] text-[#122B32] font-semibold">
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Mathematical Paradigm</th>
                <th className="py-2.5 px-3 text-right">Test MAE</th>
                <th className="py-2.5 px-3 text-right">Test RMSE</th>
                <th className="py-2.5 px-3 text-right">Latency</th>
                <th className="py-2.5 px-3 text-center">Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2EBE7]">
              {models.map((m) => {
                const isSelected = m.id === selectedModel;
                const isBestMae = m.mae === lowestMae;
                const isBestSpeed = m.latency_ms === lowestLatency;

                return (
                  <tr
                    key={m.id}
                    onClick={() => {
                      onSelectModel(m.id);
                    }}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-[#E8F3F1] font-medium"
                        : "hover:bg-[#F8FAFC]"
                    }`}
                  >
                    <td className="py-3 px-3">
                      <div className="font-semibold text-[#122B32]">{m.name}</div>
                      <div className="text-[11px] text-[#4A6369]">{m.library}</div>
                    </td>
                    <td className="py-3 px-3 text-[#334155]">
                      <span className="inline-block px-2 py-0.5 rounded bg-white border border-[#D5DFDB] text-[11px]">
                        {m.paradigm}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-[#122B32]">
                      {m.mae.toFixed(2)}
                      {isBestMae && (
                        <span className="ml-1 text-[10px] text-emerald-700 bg-emerald-100 px-1 py-0.2 rounded font-sans">
                          Best
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-[#4A6369]">
                      {m.rmse.toFixed(2)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-[#4A6369]">
                      {m.latency_ms.toFixed(2)} ms
                      {isBestSpeed && (
                        <span className="ml-1 text-[10px] text-blue-700 bg-blue-100 px-1 py-0.2 rounded font-sans">
                          Fast
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-center">
                      {isSelected ? (
                        <span className="inline-flex items-center gap-1 text-[#0A6E73] font-semibold text-xs">
                          <CheckCircle className="w-4 h-4" /> Selected
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectModel(m.id);
                          }}
                          className="px-2 py-1 text-[11px] font-medium border border-[#D5DFDB] rounded bg-white hover:bg-[#0A6E73] hover:text-white hover:border-[#0A6E73] transition-colors"
                        >
                          Select
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Key Viva / Academic Takeaways Box */}
        <div className="mt-5 p-3.5 bg-[#F3F6F4] border border-[#D5DFDB] rounded text-xs text-[#334155] space-y-1.5">
          <p className="font-semibold text-[#122B32] flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-[#0A6E73]" />
            Engineering & Thesis Takeaway:
          </p>
          <ul className="list-disc list-inside space-y-1 text-[#4A6369] pl-1">
            <li>
              <strong>Benchmark Outperformed:</strong> All 3 predictive models (HistGBR, PyTorch LSTM, Holt-Winters) comfortably beat the naive historical baseline (~4.84 MAE vs ~3.51 MAE).
            </li>
            <li>
              <strong>Paradigms:</strong> HistGBR provides robust tabular feature interaction, Holt-Winters models smooth diurnal seasonality, and PyTorch LSTM captures sequential time dynamics.
            </li>
          </ul>
        </div>

        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-[#122B32] text-white rounded text-xs font-semibold hover:bg-[#0A6E73] transition-colors"
          >
            Close Leaderboard
          </button>
        </div>
      </div>
    </div>
  );
}
