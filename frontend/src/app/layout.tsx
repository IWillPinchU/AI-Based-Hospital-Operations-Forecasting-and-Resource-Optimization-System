import type { Metadata } from "next";
import { Chivo, Atkinson_Hyperlegible } from "next/font/google";
import { AlertCircle } from "lucide-react";
import "./globals.css";
import { ThemeProvider } from "@/lib/ThemeContext";

const chivo = Chivo({
  subsets: ["latin"],
  variable: "--font-chivo",
  display: "swap",
  weight: ["400", "600", "700", "900"],
});

const atkinson = Atkinson_Hyperlegible({
  subsets: ["latin"],
  variable: "--font-atkinson",
  display: "swap",
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "Hospital Operations Forecasting and Resource Optimization System",
  description:
    "Decision-support system for hospital operations, arrival forecasting, and capacity management.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${chivo.variable} ${atkinson.variable}`}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('hospital_theme');
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  if (saved === 'dark' || (!saved && prefersDark)) {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen flex flex-col bg-[var(--canvas)] text-[var(--ink)] antialiased transition-colors duration-150">
        <ThemeProvider>
          {/* Persistent Advisory Header Banner */}
          <aside
            role="note"
            aria-label="Clinical Decision-Support Advisory Notice"
            className="bg-[#FFFBEB] border-b border-[#D9730D]/30 px-4 py-2.5 text-xs text-[#92400E] flex items-center justify-center gap-2"
          >
            <AlertCircle className="w-4 h-4 text-[#D9730D] shrink-0" aria-hidden="true" />
            <p className="font-medium text-center">
              <strong>Advisory notice:</strong> Recommendations are decision-support outputs based on provisional constraints and require human clinical verification before execution.
            </p>
          </aside>

          {/* Main Application Container */}
          <div className="flex-1 flex flex-col">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}
