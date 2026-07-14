/**
 * Report generation API calls. Mirrors app/api/routes/reports.py.
 */

import { apiRequest, ApiError } from "./client.js";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function generateReport({ keyword, language, newspaper, edition, articles, token }) {
  return apiRequest("/reports/generate", {
    method: "POST",
    body: {
      keyword,
      language,
      newspaper: newspaper || null,
      edition: edition || null,
      articles: articles.map((a) => ({
        title: a.title,
        source_name: a.source_name,
        url: a.url,
        description: a.description,
        image_url: a.image_url,
        published_at: a.published_at,
        content: a.content,
      })),
    },
    token,
  });
}

export function listReports(token) {
  return apiRequest("/reports", { token });
}

/**
 * The download route requires a Bearer token, so a plain <a href> won't
 * work (the browser sends no auth header on a normal navigation). This
 * fetches the PDF with the token attached, then triggers a real file
 * download via a temporary object URL.
 */
export async function downloadReport({ downloadUrl, token, filename }) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${downloadUrl}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new ApiError("Could not reach the server to download the report.", 0);
  }

  if (!response.ok) {
    throw new ApiError(`Could not download the report (status ${response.status}).`, response.status);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || "newspulse-report.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

