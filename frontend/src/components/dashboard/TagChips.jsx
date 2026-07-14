import { useState } from "react";

/**
 * Renders predefined industry tags plus the user's own custom tags.
 * Multiple tags can be selected at once — each click toggles that tag
 * in or out of the selection (not a single-select replace). Custom tags
 * get a small "x" to delete them; predefined tags cannot be removed
 * (they're shared, and vary by the currently selected search language).
 */
export default function TagChips({ tags, selectedTags, onToggleTag, onAddTag, onDeleteTag }) {
  const [newTag, setNewTag] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState("");

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newTag.trim()) return;
    setIsAdding(true);
    setError("");
    try {
      await onAddTag(newTag.trim());
      setNewTag("");
    } catch (err) {
      setError(err.message || "Could not add tag.");
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="tag-chips">
      {selectedTags.length > 0 && (
        <p className="tag-chips__hint">
          {selectedTags.length} tag{selectedTags.length === 1 ? "" : "s"} selected — searching for
          any of them
        </p>
      )}

      <div className="tag-chips__list">
        {tags.map((t) => {
          const key = t.is_custom ? `custom-${t.id}` : `predefined-${t.tag}`;
          const isActive = selectedTags.includes(t.tag);
          return (
            <span key={key} className={`tag-chip ${isActive ? "tag-chip--active" : ""}`}>
              <button
                type="button"
                className="tag-chip__label"
                onClick={() => onToggleTag(t.tag)}
                aria-pressed={isActive}
                title={isActive ? `Remove "${t.tag}" from search` : `Add "${t.tag}" to search`}
              >
                {t.tag}
              </button>
              {t.is_custom && (
                <button
                  type="button"
                  className="tag-chip__remove"
                  aria-label={`Delete tag ${t.tag}`}
                  onClick={() => onDeleteTag(t.id)}
                >
                  ×
                </button>
              )}
            </span>
          );
        })}
      </div>

      <form className="tag-chips__add" onSubmit={handleAdd}>
        <input
          type="text"
          value={newTag}
          onChange={(e) => setNewTag(e.target.value)}
          placeholder="Add a custom tag…"
          maxLength={100}
        />
        <button type="submit" disabled={isAdding || !newTag.trim()}>
          {isAdding ? "Adding…" : "+ Add"}
        </button>
      </form>
      {error && <p className="tag-chips__error">{error}</p>}
    </div>
  );
}
