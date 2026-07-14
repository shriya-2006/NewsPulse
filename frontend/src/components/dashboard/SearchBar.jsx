export default function SearchBar({ value, onChange, onSubmit }) {
  return (
    <form className="search-bar" onSubmit={onSubmit}>
      <svg
        className="search-bar__icon"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="7" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        type="text"
        placeholder="Search by keyword — Steel, Coal, Iron Ore, RINL, Exports…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Search news by keyword"
      />
      <button type="submit" className="search-bar__submit">
        Search
      </button>
    </form>
  );
}
