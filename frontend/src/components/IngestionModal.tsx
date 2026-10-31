"use client";

import React, { useState, useRef } from "react";
import { Upload, X, CheckCircle2, AlertTriangle, FileText } from "lucide-react";
import { uploadOperationalCsv } from "@/lib/api";
import { IngestionResponse } from "@/lib/types";
import { formatUtcDateTime } from "@/lib/formatters";

interface IngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (response: IngestionResponse) => void;
}

export function IngestionModal({ isOpen, onClose, onSuccess }: IngestionModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IngestionResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setResult(null);
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!selected.name.toLowerCase().endsWith(".csv")) {
        setError("Invalid file format. Please select a .csv operational file.");
        setFile(null);
        return;
      }
      setFile(selected);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await uploadOperationalCsv(file);
      setResult(res);
      onSuccess(res);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to upload operational data.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setError(null);
    setResult(null);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="bg-white rounded border border-[#D5DFDB] max-w-lg w-full p-6 shadow-lg">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#D5DFDB]">
          <div>
            <h2 id="modal-title" className="font-heading text-lg font-bold text-[#122B32]">
              Upload operational data
            </h2>
            <p className="text-xs text-[#4A6369] mt-0.5">
              Select an hourly hospital operations CSV file to update live models
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-[#4A6369] hover:text-[#122B32] p-1 rounded transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="py-5 space-y-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
            id="csv-file-input"
          />

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#D5DFDB] hover:border-[#0A6E73] bg-[#F3F6F4] p-6 rounded text-center cursor-pointer transition-colors"
          >
            <Upload className="w-8 h-8 text-[#0A6E73] mx-auto mb-2" />
            <p className="text-sm font-semibold text-[#122B32]">
              {file ? file.name : "Choose a CSV file or drag it here"}
            </p>
            <p className="text-xs text-[#4A6369] mt-1">
              Required columns: timestamp, ed_arrivals, ed_patients, available_beds, icu_occupancy_pct, nurses_available, doctors_available
            </p>
          </div>

          {/* Selected File Badge */}
          {file && (
            <div className="flex items-center gap-2 p-2.5 bg-white border border-[#D5DFDB] rounded text-xs text-[#122B32]">
              <FileText className="w-4 h-4 text-[#0A6E73] shrink-0" />
              <span className="font-medium truncate flex-1">{file.name}</span>
              <span className="text-[#4A6369]">
                {(file.size / 1024).toFixed(1)} KB
              </span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-[#FFF5F5] border border-[#F87171] rounded text-xs text-[#B91C1C] flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">Upload failed</p>
                <p className="mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* Success Summary */}
          {result && (
            <div className="p-3 bg-[#F0FDF4] border border-[#4ADE80] rounded text-xs text-[#166534] flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1 space-y-1">
                <p className="font-semibold">Data ingested successfully</p>
                <p>
                  Processed <strong>{result.rows_processed}</strong> rows (
                  <strong>{result.rows_inserted}</strong> inserted,{" "}
                  <strong>{result.rows_updated}</strong> updated).
                </p>
                <p className="text-[#4A6369]">
                  Latest timestamp: {formatUtcDateTime(result.latest_timestamp)}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#D5DFDB]">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-[#4A6369] hover:text-[#122B32] transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || loading}
            className="inline-flex items-center gap-2 bg-[#0A6E73] hover:bg-[#08565A] text-white text-sm font-semibold px-4 py-2 rounded transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Upload className="w-4 h-4" />
            <span>{loading ? "Processing..." : "Upload CSV"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
