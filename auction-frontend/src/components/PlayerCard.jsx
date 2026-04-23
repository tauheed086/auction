import "./PlayerCard.css";
import { resolveImageUrl } from "../api";

function getRoleLabel(role) {
  const labels = {
    batsman: "Batsman",
    bowler: "Bowler",
    allrounder: "All-Rounder",
  };
  return labels[role] || role;
}

function PlayerCard({
  player,
  actionLabel,
  onAction,
  disabledAction = false,
  variant = "featured",
}) {
  const imageUrl = resolveImageUrl(player);
  const roleLabel = getRoleLabel(player.role);
  const showSaleMeta = Boolean(
    player.is_sold || player.sold_team || player.sold_points
  );

  return (
    <div className={`card ${variant === "compact" ? "card-compact" : "card-featured"}`}>
      <div className="card-details">
        <h3 className="card-title">Auction Player</h3>

        <div className="info-row">
          <span className="field-label">Name:</span>
          <span className="field-value">{player.name}</span>
        </div>
        <div className="info-row">
          <span className="field-label">Role:</span>
          <span className="field-value">{roleLabel}</span>
        </div>
        {showSaleMeta && (
          <>
            <div className="info-row">
              <span className="field-label">Sold To:</span>
              <span className="field-value">{player.sold_team || "-"}</span>
            </div>
            <div className="info-row">
              <span className="field-label">Points:</span>
              <span className="field-value">
                {player.sold_points ?? "-"}
              </span>
            </div>
          </>
        )}

        {actionLabel && onAction && (
          <button
            className="action-button"
            onClick={() => onAction(player.id)}
            disabled={disabledAction}
          >
            {actionLabel}
          </button>
        )}
      </div>

      <div className="card-media">
        {imageUrl ? (
          <img src={imageUrl} alt={player.name} />
        ) : (
          <div className="image-placeholder">No Image</div>
        )}

        {player.is_sold && <div className="status-stamp sold-stamp">SOLD</div>}
        {!player.is_sold && player.is_skipped && (
          <div className="status-stamp skipped-stamp">SKIPPED</div>
        )}
      </div>
    </div>
  );
}

export default PlayerCard;
