/**
 * Formats an ISO UTC timestamp into readable hospital format:
 * e.g. "Oct 30, 2026, 23:00 UTC"
 */
export function formatUtcDateTime(isoString?: string | null): string {
  if (!isoString) return "No data recorded";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;

    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];

    const month = months[d.getUTCMonth()];
    const day = d.getUTCDate();
    const year = d.getUTCFullYear();
    const hours = String(d.getUTCHours()).padStart(2, "0");
    const minutes = String(d.getUTCMinutes()).padStart(2, "0");

    return `${month} ${day}, ${year}, ${hours}:${minutes} UTC`;
  } catch {
    return isoString;
  }
}

/**
 * Formats short time for chart axes or compact cards:
 * e.g. "23:00 UTC"
 */
export function formatUtcTime(isoString?: string | null): string {
  if (!isoString) return "--:--";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    const hours = String(d.getUTCHours()).padStart(2, "0");
    const minutes = String(d.getUTCMinutes()).padStart(2, "0");
    return `${hours}:${minutes} UTC`;
  } catch {
    return isoString;
  }
}

/**
 * Translates backend category enums to friendly hospital names
 * (Sentence case, human-readable).
 */
export function formatCategoryName(category: string): string {
  switch (category.toUpperCase()) {
    case "STAFFING_NURSE":
      return "Nurse staffing";
    case "BED_MANAGEMENT":
      return "Bed management";
    case "STAFFING_DOCTOR":
      return "Doctor staffing";
    default:
      return category
        .toLowerCase()
        .replace(/_/g, " ")
        .replace(/^\w/, (c) => c.toUpperCase());
  }
}
