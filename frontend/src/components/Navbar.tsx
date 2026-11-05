import React from "react";
import { Activity, Upload, Clock, RefreshCw, BarChart3, WifiOff, FileText, Sun, Moon } from "lucide-react";
import { formatUtcDateTime } from "@/lib/formatters";
import { useTheme } from "@/lib/ThemeContext";
import { useIsMounted } from "@/lib/useIsMounted";

interface NavbarProps {
  latestTimestamp?: string | null;
  onOpenUpload: () => void;
  onOpenShiftReport?: () => void;
  isIngesting?: boolean;
  lastRefreshedAt?: Date | null;
  livePaused?: boolean;
  wsStatus?: "connected" | "connecting" | "disconnected";
  activeTab?: "live" | "history";
  onTabChange?: (tab: "live" | "history") => void;
}

function formatLocalTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function Navbar({
  latestTimestamp,
  onOpenUpload,
  onOpenShiftReport,
  isIngesting,
  lastRefreshedAt,
  livePaused,
  wsStatus = "disconnected",
  activeTab = "live",
  onTabChange,
}: NavbarProps) {
  const { theme, toggleTheme } = useTheme();
  const mounted = useIsMounted();

  return (
    <header className="bg-white border-b border-[#D5DFDB] sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Navigation Switcher Tabs */}
        {onTabChange && (
          <nav className="flex items-center gap-1 bg-[#F3F6F4] p-1 rounded border border-[#D5DFDB] shrink-0">
            <button
              type="button"
              onClick={() => onTabChange("live")}
              className={`flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 text-xs font-semibold rounded transition-colors cursor-pointer ${
                activeTab === "live"
                  ? "bg-white text-[#0A6E73] shadow-xs"
                  : "text-[#4A6369] hover:text-[#122B32]"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Live Monitor</span>
            </button>
            <button
              type="button"
              onClick={() => onTabChange("history")}
              className={`flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 text-xs font-semibold rounded transition-colors cursor-pointer ${
                activeTab === "history"
                  ? "bg-white text-[#0A6E73] shadow-xs"
                  : "text-[#4A6369] hover:text-[#122B32]"
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Historical Analytics</span>
            </button>
          </nav>
        )}

        {/* Right: Timestamp and Action Buttons */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Real-time Connection Indicator */}
          <div
            className="hidden md:flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded border whitespace-nowrap bg-[#F3F6F4] border-[#D5DFDB]"
            title={
              wsStatus === "connected"
                ? "Connected to real-time WebSocket feed. Updates arrive instantly."
                : "WebSocket disconnected. Falling back to background polling."
            }
          >
            <span
              className={`w-2 h-2 rounded-full ${
                wsStatus === "connected"
                  ? "bg-emerald-500 animate-pulse"
                  : wsStatus === "connecting"
                  ? "bg-amber-400 animate-ping"
                  : "bg-slate-400"
              }`}
            />
            <span className="font-medium text-[#122B32]">
              {wsStatus === "connected"
                ? "Live (WebSocket)"
                : wsStatus === "connecting"
                ? "Connecting..."
                : "Polling (10s)"}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#4A6369] bg-[#F3F6F4] px-3 py-1.5 rounded border border-[#D5DFDB] whitespace-nowrap">
            <Clock className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
            <span>Latest data:</span>
            <span className="font-semibold text-[#122B32]">
              {formatUtcDateTime(latestTimestamp)}
            </span>
          </div>

          {lastRefreshedAt && (
            <div className="hidden xl:flex items-center gap-1.5 text-xs text-[#4A6369] bg-[#F3F6F4] px-3 py-1.5 rounded border border-[#D5DFDB] whitespace-nowrap">
              <RefreshCw className="w-3.5 h-3.5 text-[#0A6E73]" aria-hidden="true" />
              <span>Last refreshed:</span>
              <span className="font-semibold text-[#122B32]">
                {formatLocalTime(lastRefreshedAt)}
              </span>
            </div>
          )}

          {onOpenShiftReport && (
            <button
              type="button"
              onClick={onOpenShiftReport}
              className="inline-flex items-center gap-1.5 bg-white border border-[#D5DFDB] hover:bg-[#F3F6F4] text-[#122B32] text-xs sm:text-sm font-semibold px-2.5 sm:px-3 py-2 rounded transition-colors cursor-pointer"
              title="Download formal shift handover documentation (PDF or Excel)"
            >
              <FileText className="w-4 h-4 text-[#0A6E73]" aria-hidden="true" />
              <span className="hidden sm:inline">Shift Report</span>
              <span className="sm:hidden">Report</span>
            </button>
          )}

          {/* Dark / Light Mode Switcher */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={mounted && theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            title={mounted && theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            suppressHydrationWarning
            className="inline-flex items-center justify-center w-9 h-9 bg-white border border-[#D5DFDB] hover:bg-[#F3F6F4] text-[#122B32] rounded transition-colors cursor-pointer shrink-0"
          >
            {mounted && theme === "dark" ? (
              <Sun className="w-4 h-4 text-amber-400" aria-hidden="true" />
            ) : (
              <Moon className="w-4 h-4 text-[#0A6E73]" aria-hidden="true" />
            )}
          </button>

          <button
            type="button"
            onClick={onOpenUpload}
            disabled={isIngesting}
            className="inline-flex items-center gap-2 bg-[#0A6E73] hover:bg-[#08565A] text-white text-sm font-semibold px-3.5 py-2 rounded transition-colors shadow-none focus-visible:ring-2 focus-visible:ring-[#0A6E73] cursor-pointer disabled:opacity-60"
          >
            <Upload className="w-4 h-4" aria-hidden="true" />
            <span className="hidden sm:inline">Upload CSV</span>
            <span className="sm:inline hidden"></span>
            <span className="sm:hidden">Upload</span>
          </button>
        </div>
      </div>
      <div role="status" aria-live="polite">
        {livePaused && (
          <div className="bg-[#FFFBEB] border-t border-[#D9730D]/30 px-4 py-2 text-xs text-[#92400E] flex items-center justify-center gap-2">
            <WifiOff className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <span>Live updates paused. Showing last data.</span>
          </div>
        )}
      </div>
    </header>
  );
}
