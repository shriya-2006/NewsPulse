import ArticleCard from "./ArticleCard.jsx";

function SkeletonCard() {
  return (
    <div className="article-skeleton" aria-hidden="true">
      <div className="article-skeleton__checkbox" />
      <div className="article-skeleton__body">
        <div className="article-skeleton__line article-skeleton__line--meta" />
        <div className="article-skeleton__line article-skeleton__line--title" />
        <div className="article-skeleton__line article-skeleton__line--text" />
        <div className="article-skeleton__line article-skeleton__line--text article-skeleton__line--short" />
      </div>
    </div>
  );
}

/**
 * Four states, in priority order: hasn't searched yet -> loading ->
 * error -> no results -> results (+ pagination).
 */
export default function NewsPanel({
  hasSearched,
  isLoading,
  error,
  articles,
  notice,
  selectedUrls,
  onToggleArticle,
  page,
  hasMore,
  onPageChange,
  providerUsed,
}) {
  if (!hasSearched) {
    return (
      <section className="news-panel" aria-label="News articles">
        <div className="news-panel__empty">
          <div className="news-panel__empty-icon" aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <line x1="7" y1="8" x2="17" y2="8" />
              <line x1="7" y1="12" x2="17" y2="12" />
              <line x1="7" y1="16" x2="12" y2="16" />
            </svg>
          </div>
          <h3>Articles will appear here</h3>
          <p>
            Run a search using the keyword bar above to pull matching news
            articles. You'll be able to select the ones you want and add
            them to a report.
          </p>
        </div>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="news-panel news-panel--list" aria-label="News articles" aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </section>
    );
  }

  if (error) {
    return (
      <section className="news-panel" aria-label="News articles">
        <div className="news-panel__empty news-panel__empty--error">
          <div className="news-panel__empty-icon news-panel__empty-icon--error" aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <circle cx="12" cy="12" r="9" />
              <line x1="12" y1="8" x2="12" y2="13" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h3>Couldn't load news</h3>
          <p>{error}</p>
        </div>
      </section>
    );
  }

  if (articles.length === 0) {
    return (
      <section className="news-panel" aria-label="News articles">
        <div className="news-panel__empty">
          <div className="news-panel__empty-icon" aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3>No articles found</h3>
          <p>{notice || "Try a different keyword, language, or date range."}</p>
        </div>
      </section>
    );
  }

  return (
    <div className="news-panel-wrapper">
      {providerUsed && (
        <p className="news-panel__provider-note">
          Results from{" "}
          {providerUsed === "gnews" && "GNews"}
          {providerUsed === "newsdata" && "NewsData.io"}
          {providerUsed === "google_rss" && "Google News"}
        </p>
      )}

      <section className="news-panel news-panel--list" aria-label="News articles">
        {articles.map((article) => (
          <ArticleCard
            key={article.url}
            article={article}
            isSelected={selectedUrls.has(article.url)}
            onToggle={() => onToggleArticle(article)}
          />
        ))}
      </section>

      {(page > 1 || hasMore) && (
        <div className="news-panel__pagination">
          <button
            type="button"
            className="pagination-btn"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            ← Previous
          </button>
          <span className="pagination-current">Page {page}</span>
          <button
            type="button"
            className="pagination-btn"
            onClick={() => onPageChange(page + 1)}
            disabled={!hasMore}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
