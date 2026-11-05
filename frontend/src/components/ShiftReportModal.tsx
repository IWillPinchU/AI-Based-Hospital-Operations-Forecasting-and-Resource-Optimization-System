"use client";

import React, { useState } from "react";
import {
  FileText,
  FileSpreadsheet,
  X,
  Clock,
  Download,
  AlertTriangle,
  CheckCircle2,
  Layers,
  Activity,
  Users,
} from "lucide-react";
import { downloadShiftReport } from "@/lib/api";

interface ShiftReportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ShiftHours = 8 | 12 | 24;
type ReportFormat = "pdf" | "excel";

export function ShiftReportModal({ isOpen, onClose }: ShiftReportModalProps) {
  const [hours, setHours] = useState<ShiftHours>(12);
  const [format, setFormat] = useState<ReportFormat>("pdf");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await downloadShiftReport({ hours, format });
      setSuccessMsg(`Successfully generated ${hours}h ${format.toUpperCase()} shift handover report.`);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to generate report.");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setError(null);
    setSuccessMsg(null);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-4"
    >
      <div className="bg-white rounded border border-[#D5DFDB] max-w-lg w-full p-4 sm:p-6 shadow-xl space-y-4 sm:space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#D5DFDB]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-[#F3F6F4] rounded border border-[#D5DFDB] text-[#0A6E73]">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 id="report-modal-title" className="font-heading text-lg font-bold text-[#122B32]">
                Generate Shift Handover Report
              </h2>
              <p className="text-xs text-[#4A6369] mt-0.5">
                Download formal clinical handover documentation for shift changes and audits
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-[#4A6369] hover:text-[#122B32] p-1 rounded transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Shift Duration Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-[#122B32] uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-[#0A6E73]" />
            1. Select Shift Duration
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { val: 8 as ShiftHours, label: "8 Hours", desc: "Day / Night Shift" },
              { val: 12 as ShiftHours, label: "12 Hours", desc: "Acute Care Shift" },
              { val: 24 as ShiftHours, label: "24 Hours", desc: "Full-Day Audit" },
            ].map((item) => (
              <button
                key={item.val}
                type="button"
                onClick={() => setHours(item.val)}
                className={`p-3 rounded border text-left transition-all cursor-pointer ${
                  hours === item.val
                    ? "border-[#0A6E73] bg-[#0A6E73]/5 ring-1 ring-[#0A6E73]"
                    : "border-[#D5DFDB] bg-white hover:bg-[#F3F6F4]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-heading text-sm font-bold text-[#122B32]">
                    {item.label}
                  </span>
                  {hours === item.val && (
                    <div className="w-2 h-2 rounded-full bg-[#0A6E73]" />
                  )}
                </div>
                <p className="text-[11px] text-[#4A6369] mt-0.5">{item.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Report Format Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-[#122B32] uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[#0A6E73]" />
            2. Choose Document Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            {/* Option 1: PDF */}
            <div
              onClick={() => setFormat("pdf")}
              className={`p-3.5 rounded border transition-all cursor-pointer flex flex-col justify-between ${
                format === "pdf"
                  ? "border-[#0A6E73] bg-[#0A6E73]/5 ring-1 ring-[#0A6E73]"
                  : "border-[#D5DFDB] bg-white hover:bg-[#F3F6F4]"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-[#FFF5F5] text-[#C92A2A]">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-heading text-sm font-bold text-[#122B32]">
                      Executive PDF
                    </h4>
                    <span className="text-[10px] text-[#0A6E73] font-medium">
                      Printable Document
                    </span>
                  </div>
                </div>
                {format === "pdf" && (
                  <div className="w-2 h-2 rounded-full bg-[#0A6E73]" />
                )}
              </div>
              <p className="text-xs text-[#4A6369] mt-2 leading-relaxed">
                Clean clinical layout with executive scorecard, hourly telemetry, alert timeline, and supervisor handover guidance.
              </p>
            </div>

            {/* Option 2: Excel */}
            <div
              onClick={() => setFormat("excel")}
              className={`p-3.5 rounded border transition-all cursor-pointer flex flex-col justify-between ${
                format === "excel"
                  ? "border-[#0A6E73] bg-[#0A6E73]/5 ring-1 ring-[#0A6E73]"
                  : "border-[#D5DFDB] bg-white hover:bg-[#F3F6F4]"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-[#F0FDF4] text-[#166534]">
                    <FileSpreadsheet className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-heading text-sm font-bold text-[#122B32]">
                      Excel Workbook
                    </h4>
                    <span className="text-[10px] text-[#0A6E73] font-medium">
                      .xlsx Data Export
                    </span>
                  </div>
                </div>
                {format === "excel" && (
                  <div className="w-2 h-2 rounded-full bg-[#0A6E73]" />
                )}
              </div>
              <p className="text-xs text-[#4A6369] mt-2 leading-relaxed">
                Multi-tab workbook containing KPI Summary, Hourly Telemetry records, and Anomaly Incident audit logs.
              </p>
            </div>
          </div>
        </div>

        {/* Report Content Scope Preview */}
        <div className="bg-[#F3F6F4] rounded border border-[#D5DFDB] p-3 text-xs text-[#4A6369] space-y-1.5">
          <div className="font-semibold text-[#122B32] flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#0A6E73]" />
            Shift Report Includes:
          </div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px]">
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-[#0A6E73]" /> Total Inflow & Peak Surge
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3 text-[#0A6E73]" /> Staffing & Patient Ratios
            </span>
            <span className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-[#D97706]" /> Anomaly Incidents & Status
            </span>
            <span className="flex items-center gap-1">
              <Layers className="w-3 h-3 text-[#2563EB]" /> Next-Hour Handover Forecast
            </span>
          </div>
        </div>

        {/* Alerts / Success Feedback */}
        {error && (
          <div className="p-3 bg-[#FFF5F5] border border-[#F87171] rounded text-xs text-[#B91C1C] flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold">Generation failed</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-[#F0FDF4] border border-[#4ADE80] rounded text-xs text-[#166534] flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#D5DFDB]">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-xs font-medium text-[#4A6369] hover:text-[#122B32] transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDownload}
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2 rounded text-xs font-semibold bg-[#0A6E73] text-white hover:bg-[#08565A] transition-colors cursor-pointer disabled:opacity-50"
          >
            <Download className={`w-3.5 h-3.5 ${loading ? "animate-bounce" : ""}`} />
            <span>
              {loading
                ? `Compiling ${format.toUpperCase()}...`
                : `Download ${hours}h ${format.toUpperCase()} Report`}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

