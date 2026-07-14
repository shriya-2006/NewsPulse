const DATE_FILTERS = [
  { value: "any", label: "Any time" },
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "custom", label: "Custom range" },
];

/**
 * Cascading filter bar: Language -> Newspaper -> Edition -> Date.
 * `languages`, `newspapers`, and `editions` are all fetched by the
 * parent from the backend (GET /news/languages, /news/newspapers,
 * /news/editions) — nothing here is a hardcoded list, so a newspaper or
 * edition added on the backend shows up automatically with no frontend
 * changes.
 *
 * Edition no longer requires a newspaper to be selected first — picking
 * an edition on its own (e.g. "Visakhapatnam") searches across every
 * newspaper for that edition/location instead of one specific outlet.
 */
export default function FilterBar({
  languages,
  language,
  onLanguageChange,
  newspapers,
  newspaper,
  onNewspaperChange,
  editions,
  isLoadingEditions,
  edition,
  onEditionChange,
  dateFilter,
  onDateFilterChange,
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
}) {
  const today = new Date().toISOString().split("T")[0];

  let editionContent;
  if (isLoadingEditions) {
    editionContent = <option value="">Loading editions…</option>;
  } else if (editions.length === 0) {
    editionContent = <option value="">No editions available.</option>;
  } else {
    editionContent = (
      <>
        <option value="">{newspaper ? "All editions" : "Any edition"}</option>
        {editions.map((ed) => (
          <option key={ed} value={ed}>
            {ed}
          </option>
        ))}
      </>
    );
  }

  return (
    <div className="filter-bar">
      <div className="filter-bar__group" role="group" aria-label="Filter by language">
        <span className="filter-bar__label">Language</span>
        <div className="filter-bar__pills">
          {languages.map((lang) => (
            <button
              key={lang.code}
              type="button"
              className={`filter-pill ${language === lang.code ? "filter-pill--active" : ""}`}
              onClick={() => onLanguageChange(lang.code)}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-bar__group">
        <span className="filter-bar__label">Newspaper</span>
        <select
          className="filter-select"
          value={newspaper}
          onChange={(e) => onNewspaperChange(e.target.value)}
        >
          <option value="">All newspapers</option>
          {newspapers.map((n) => (
            <option key={n.key} value={n.key}>
              {n.label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-bar__group">
        <span className="filter-bar__label">
          Edition
          {!newspaper && <span className="filter-bar__label-hint"> (any newspaper)</span>}
        </span>
        <select
          className="filter-select"
          value={edition}
          onChange={(e) => onEditionChange(e.target.value)}
          disabled={isLoadingEditions || editions.length === 0}
        >
          {editionContent}
        </select>
      </div>

      <div className="filter-bar__group">
        <span className="filter-bar__label">Date</span>
        <div className="filter-bar__date-row">
          <select
            className="filter-select filter-select--compact"
            value={dateFilter}
            onChange={(e) => onDateFilterChange(e.target.value)}
          >
            {DATE_FILTERS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          {dateFilter === "custom" && (
            <div className="filter-bar__date-range">
              <label className="filter-bar__date-range-label">
                From
                <input
                  type="date"
                  className="filter-date-input"
                  value={dateFrom}
                  max={dateTo || today}
                  onChange={(e) => onDateFromChange(e.target.value)}
                />
              </label>
              <label className="filter-bar__date-range-label">
                To
                <input
                  type="date"
                  className="filter-date-input"
                  value={dateTo}
                  min={dateFrom || undefined}
                  max={today}
                  onChange={(e) => onDateToChange(e.target.value)}
                />
              </label>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
