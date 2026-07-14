import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ApiError } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import {
  searchNews,
  fetchLanguages,
  fetchNewspapers,
  fetchEditions,
  fetchTags,
  addTag,
  deleteTag,
} from "../api/news.js";
import { generateReport, downloadReport } from "../api/reports.js";
import Navbar from "../components/dashboard/Navbar.jsx";
import SearchBar from "../components/dashboard/SearchBar.jsx";
import FilterBar from "../components/dashboard/FilterBar.jsx";
import TagChips from "../components/dashboard/TagChips.jsx";
import NewsPanel from "../components/dashboard/NewsPanel.jsx";
import "./Dashboard.css";

const PAGE_SIZE = 10;

const DEFAULT_FILTERS = {
  keyword: "",
  language: "en",
  newspaper: "",
  edition: "",
  dateFilter: "any",
  dateFrom: "",
  dateTo: "",
};

export default function Dashboard() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();

  // --- Search state ---
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  // Multiple tags can be active at once (issue: tag selection was
  // single-select before — clicking a second tag now adds to the
  // selection instead of replacing it).
  const [selectedTags, setSelectedTags] = useState([]);
  const [page, setPage] = useState(1);
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedArticles, setSelectedArticles] = useState(new Map());
  const [reportNotice, setReportNotice] = useState(null); // { type: 'error'|'success', text }
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // --- Reference data ---
  // Languages: fetched once — this is the top of the cascade, so nothing
  // else needs to happen before it's available.
  const [languages, setLanguages] = useState([]);
  useEffect(() => {
    fetchLanguages(token)
      .catch(() => [])
      .then((data) => setLanguages(data || []));
  }, [token]);

  // Newspapers + tags: scoped to the currently selected search language,
  // re-fetched whenever it changes, so Telugu/Hindi newspapers and tags
  // are always the actual server response for that language rather than
  // a client-side filter of a single upfront fetch.
  const [newspapers, setNewspapers] = useState([]);
  const [tags, setTags] = useState([]);

  useEffect(() => {
    fetchNewspapers({ language: filters.language, token })
      .catch(() => [])
      .then((data) => setNewspapers(data || []));
    fetchTags({ language: filters.language, token })
      .catch(() => [])
      .then((data) => setTags(data || []));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.language, token]);

  // Editions: the last link in the cascade — scoped to whichever
  // newspaper is currently selected, re-fetched every time it changes.
  // Cleared immediately (not just re-fetched) whenever there's no
  // newspaper selected, so stale editions from a previous newspaper can
  // never briefly show through.
  const [editions, setEditions] = useState([]);
  const [isLoadingEditions, setIsLoadingEditions] = useState(false);

  useEffect(() => {
    // With no newspaper selected, fetch the union of every edition
    // across all newspapers instead — editions no longer require a
    // newspaper to be picked first (a person can filter by location
    // alone, e.g. "Visakhapatnam", across every outlet).
    setIsLoadingEditions(true);
    fetchEditions({ newspaper: filters.newspaper || undefined, token })
      .then((data) => setEditions(data.editions || []))
      .catch(() => setEditions([]))
      .finally(() => setIsLoadingEditions(false));
  }, [filters.newspaper, token]);

  const handleUnauthorized = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const performSearch = async (searchFilters, searchPage) => {
    setIsSearching(true);
    setSearchError("");
    setHasSearched(true);
    try {
      const data = await searchNews({
        keyword: searchFilters.keyword,
        language: searchFilters.language,
        newspaper: searchFilters.newspaper || undefined,
        edition: searchFilters.edition || undefined,
        dateFilter: searchFilters.dateFilter,
        dateFrom: searchFilters.dateFilter === "custom" ? searchFilters.dateFrom : undefined,
        dateTo: searchFilters.dateFilter === "custom" ? searchFilters.dateTo : undefined,
        page: searchPage,
        pageSize: PAGE_SIZE,
        token,
      });
      setResults(data);
      setPage(data.page);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      setSearchError(
        err instanceof ApiError ? err.message : "Something went wrong while searching."
      );
      setResults(null);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!filters.keyword.trim() || filters.keyword.trim().length < 2) {
      setSearchError("Enter at least 2 characters to search.");
      setHasSearched(true);
      return;
    }
    setSelectedTags([]);
    performSearch(filters, 1);
  };

  // Toggles one tag in/out of the multi-select set, then searches using
  // every currently-selected tag combined (OR'd together, so the search
  // catches articles matching any of the selected topics).
  // IMPORTANT: side effects (setFilters, performSearch) must NOT live
  // inside the updater function passed to setSelectedTags — React is
  // allowed to invoke that updater more than once per call (and does,
  // intentionally, in development), which was silently firing the same
  // search request multiple times per click. Reading `selectedTags`
  // directly from the closure and doing the side effects in the body of
  // this handler (not inside a setState updater) fixes that.
  const handleToggleTag = (tag) => {
    const isSelected = selectedTags.includes(tag);
    const nextTags = isSelected ? selectedTags.filter((t) => t !== tag) : [...selectedTags, tag];

    setSelectedTags(nextTags);

    const combinedKeyword = nextTags.join(" OR ");
    const nextFilters = { ...filters, keyword: combinedKeyword };
    setFilters(nextFilters);

    if (nextTags.length > 0) {
      performSearch(nextFilters, 1);
    }
  };

  const handleAddTag = async (tagText) => {
    const created = await addTag({ tag: tagText, token });
    setTags((prev) => [...prev, created]);
  };

  const handleDeleteTag = async (tagId) => {
    await deleteTag({ tagId, token });
    setTags((prev) => prev.filter((t) => t.id !== tagId));
  };

  const handleLanguageChange = (language) => {
    setFilters((f) => ({ ...f, language, newspaper: "", edition: "" }));
    setSelectedTags([]);
  };
  const handleNewspaperChange = (newspaper) => {
    setFilters((f) => ({ ...f, newspaper, edition: "" }));
  };
  const handleEditionChange = (edition) => setFilters((f) => ({ ...f, edition }));
  const handleDateFilterChange = (dateFilter) =>
    setFilters((f) => ({
      ...f,
      dateFilter,
      dateFrom: dateFilter === "custom" ? f.dateFrom : "",
      dateTo: dateFilter === "custom" ? f.dateTo : "",
    }));
  const handleDateFromChange = (dateFrom) => setFilters((f) => ({ ...f, dateFrom }));
  const handleDateToChange = (dateTo) => setFilters((f) => ({ ...f, dateTo }));

  const handlePageChange = (newPage) => {
    if (newPage < 1) return;
    performSearch(filters, newPage);
  };

  const handleToggleArticle = (article) => {
    setSelectedArticles((prev) => {
      const next = new Map(prev);
      if (next.has(article.url)) {
        next.delete(article.url);
      } else {
        next.set(article.url, article);
      }
      return next;
    });
  };

  const handleGenerateReport = async () => {
    if (selectedArticles.size === 0) return;
    setIsGeneratingReport(true);
    setReportNotice(null);
    try {
      const report = await generateReport({
        keyword: filters.keyword || selectedTags.join(" OR ") || "News Report",
        language: filters.language,
        newspaper: filters.newspaper,
        edition: filters.edition,
        articles: Array.from(selectedArticles.values()),
        token,
      });

      await downloadReport({
        downloadUrl: report.download_url,
        token,
        filename: `${report.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.pdf`,
      });

      setReportNotice({
        type: "success",
        text: `Report generated and downloaded — ${report.article_count} article${
          report.article_count === 1 ? "" : "s"
        } included.`,
      });
      setSelectedArticles(new Map());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      setReportNotice({
        type: "error",
        text:
          err instanceof ApiError
            ? err.message
            : "Something went wrong while generating the report.",
      });
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const firstName = user?.full_name?.split(" ")[0];

  return (
    <div className="dashboard">
      <Navbar />

      <main className="dashboard__content">
        <div className="dashboard__intro">
          <div>
            <span className="dashboard__eyebrow">Daily News Monitoring</span>
            <h1>{firstName ? `Welcome back, ${firstName}` : "Search & build today's report"}</h1>
          </div>
        </div>

        <div className="dashboard__panel">
          <SearchBar
            value={filters.keyword}
            onChange={(keyword) => setFilters((f) => ({ ...f, keyword }))}
            onSubmit={handleSearchSubmit}
          />

          <TagChips
            tags={tags}
            selectedTags={selectedTags}
            onToggleTag={handleToggleTag}
            onAddTag={handleAddTag}
            onDeleteTag={handleDeleteTag}
          />

          <FilterBar
            languages={languages}
            language={filters.language}
            onLanguageChange={handleLanguageChange}
            newspapers={newspapers}
            newspaper={filters.newspaper}
            onNewspaperChange={handleNewspaperChange}
            editions={editions}
            isLoadingEditions={isLoadingEditions}
            edition={filters.edition}
            onEditionChange={handleEditionChange}
            dateFilter={filters.dateFilter}
            onDateFilterChange={handleDateFilterChange}
            dateFrom={filters.dateFrom}
            onDateFromChange={handleDateFromChange}
            dateTo={filters.dateTo}
            onDateToChange={handleDateToChange}
          />
        </div>

        <div className="dashboard__panel-header">
          <h2>Results</h2>
          <button
            type="button"
            className="btn-generate"
            disabled={selectedArticles.size === 0 || isGeneratingReport}
            onClick={handleGenerateReport}
          >
            {isGeneratingReport
              ? "Generating…"
              : `Generate Report${selectedArticles.size > 0 ? ` (${selectedArticles.size})` : ""}`}
          </button>
        </div>

        {reportNotice && (
          <p className={`dashboard__report-notice dashboard__report-notice--${reportNotice.type}`}>
            {reportNotice.text}
            {reportNotice.type === "success" && (
              <>
                {" "}
                <Link to="/reports" className="dashboard__report-notice-link">
                  View in Report History →
                </Link>
              </>
            )}
          </p>
        )}

        <NewsPanel
          hasSearched={hasSearched}
          isLoading={isSearching}
          error={searchError}
          articles={results?.articles || []}
          notice={results?.notice}
          selectedUrls={new Set(selectedArticles.keys())}
          onToggleArticle={handleToggleArticle}
          page={page}
          hasMore={Boolean(results?.has_more)}
          onPageChange={handlePageChange}
          providerUsed={results?.provider_used}
        />
      </main>
    </div>
  );
}
