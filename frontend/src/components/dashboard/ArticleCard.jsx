function formatDate(isoString) {
  if (!isoString) return "Date unavailable";
  try {
    return new Date(isoString).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "Date unavailable";
  }
}

export default function ArticleCard({ article, isSelected, onToggle }) {
  return (
    <div className={`article-card ${isSelected ? "article-card--selected" : ""}`}>
      <input
        type="checkbox"
        className="article-card__checkbox"
        checked={isSelected}
        onChange={onToggle}
        aria-label={`Select article: ${article.title}`}
      />

      {article.image_url && (
        <img
          className="article-card__image"
          src={article.image_url}
          alt=""
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      )}

      <div className="article-card__body">
        <div className="article-card__meta">
          <span className="article-card__source">{article.source_name}</span>
          <span className="article-card__dot">·</span>
          <span className="article-card__date">{formatDate(article.published_at)}</span>
        </div>

        <h3 className="article-card__title">{article.title}</h3>

        {article.description && (
          <p className="article-card__description">{article.description}</p>
        )}

        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="article-card__link"
        >
          Read original article ↗
        </a>
      </div>
    </div>
  );
}
