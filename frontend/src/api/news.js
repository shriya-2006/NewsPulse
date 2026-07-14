/**
 * News search + tags API calls. Mirrors app/api/routes/news.py 1:1.
 */

import { apiRequest } from "./client.js";

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  const str = query.toString();
  return str ? `?${str}` : "";
}

export function fetchLanguages(token) {
  return apiRequest("/news/languages", { token });
}

export function fetchNewspapers({ language, token }) {
  return apiRequest(`/news/newspapers${buildQuery({ language })}`, { token });
}

export function fetchEditions({ newspaper, token }) {
  return apiRequest(`/news/editions${buildQuery({ newspaper })}`, { token });
}

export function searchNews({
  keyword,
  language,
  newspaper,
  edition,
  dateFilter,
  dateFrom,
  dateTo,
  page,
  pageSize,
  token,
}) {
  const query = buildQuery({
    keyword,
    language,
    newspaper,
    edition,
    date_filter: dateFilter,
    date_from: dateFrom,
    date_to: dateTo,
    page,
    page_size: pageSize,
  });
  return apiRequest(`/news/search${query}`, { token });
}

export function fetchTags({ language, token }) {
  return apiRequest(`/news/tags${buildQuery({ language })}`, { token });
}

export function addTag({ tag, token }) {
  return apiRequest("/news/tags", { method: "POST", body: { tag }, token });
}

export function deleteTag({ tagId, token }) {
  return apiRequest(`/news/tags/${tagId}`, { method: "DELETE", token });
}
