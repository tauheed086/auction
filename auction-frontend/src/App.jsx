import { useCallback, useEffect, useRef, useState } from "react";
import { getCurrentAuction, getPlayers } from "./api";
import PlayerCard from "./components/PlayerCard";
import LeagueBrand from "./components/LeagueBrand";
import Confetti from "react-confetti";
import { fireCelebration } from "./utils/celebration";
import viewerBackground from "../16 No..png";

function getRoleLabel(role) {
  const labels = {
    batsman: "Batsman",
    bowler: "Bowler",
    allrounder: "All-Rounder",
  };
  return labels[role] || role;
}

function getStatusMeta(player) {
  if (player.is_sold) {
    return { text: "Sold", className: "status-sold" };
  }
  if (player.is_skipped) {
    return { text: "Skipped", className: "status-skipped" };
  }
  return { text: "Available", className: "status-available" };
}

function App() {
  const [auction, setAuction] = useState(null);
  const [players, setPlayers] = useState([]);
  const [activeTab, setActiveTab] = useState("auction");
  const [confetti, setConfetti] = useState(false);
  const previousStatusRef = useRef({ playerId: null, isSold: false });
  const confettiTimerRef = useRef(null);

  const triggerConfetti = useCallback(() => {
    setConfetti(true);
    clearTimeout(confettiTimerRef.current);
    confettiTimerRef.current = setTimeout(() => setConfetti(false), 5000);
  }, []);

  const fetchViewerData = useCallback(async () => {
    try {
      const [auctionRes, playersRes] = await Promise.all([
        getCurrentAuction(),
        getPlayers(),
      ]);

      const nextAuction = auctionRes.data;
      const currentPlayer = nextAuction?.current_player || null;
      const wasSold = previousStatusRef.current.isSold;
      const oldPlayerId = previousStatusRef.current.playerId;

      if (
        currentPlayer &&
        currentPlayer.is_sold &&
        (!wasSold || oldPlayerId !== currentPlayer.id)
      ) {
        triggerConfetti();
        fireCelebration();
      }

      previousStatusRef.current = {
        playerId: currentPlayer ? currentPlayer.id : null,
        isSold: Boolean(currentPlayer?.is_sold),
      };
      setAuction(nextAuction);
      setPlayers(playersRes.data);
    } catch (error) {
      console.error("Failed to fetch viewer data", error);
    }
  }, [triggerConfetti]);

  useEffect(() => {
    const initialLoadTimeoutId = setTimeout(() => {
      void fetchViewerData();
    }, 0);
    const intervalId = setInterval(() => {
      void fetchViewerData();
    }, 2000);

    return () => {
      clearTimeout(initialLoadTimeoutId);
      clearInterval(intervalId);
      clearTimeout(confettiTimerRef.current);
    };
  }, [fetchViewerData]);

  useEffect(() => {
    document.body.classList.add("viewer-body");
    document.body.style.setProperty("--viewer-bg-image", `url("${viewerBackground}")`);
    return () => {
      document.body.classList.remove("viewer-body");
      document.body.style.removeProperty("--viewer-bg-image");
    };
  }, []);

  const currentPlayer = auction?.current_player;

  return (
    <div className="page viewer-page">
      {confetti && <Confetti recycle={false} numberOfPieces={520} />}

      <LeagueBrand />

      <div className="viewer-tabs-row">
        <div className="viewer-tabs" role="tablist" aria-label="Viewer sections">
          <button
            type="button"
            className={`viewer-tab ${activeTab === "auction" ? "is-active" : ""}`}
            onClick={() => setActiveTab("auction")}
            role="tab"
            aria-selected={activeTab === "auction"}
          >
            Auction View
          </button>
          <button
            type="button"
            className={`viewer-tab ${activeTab === "list" ? "is-active" : ""}`}
            onClick={() => setActiveTab("list")}
            role="tab"
            aria-selected={activeTab === "list"}
          >
            Player List
          </button>
        </div>
        <a href="/admin-board" className="viewer-admin-link">
          Admin Panel
        </a>
      </div>

      {activeTab === "auction" && (
        <section className="panel">
          {!currentPlayer && (
            <p className="empty-state">Waiting for admin to select a player.</p>
          )}

          {currentPlayer && (
            <div className="viewer-card-wrap">
              <PlayerCard player={currentPlayer} />
            </div>
          )}
        </section>
      )}

      {activeTab === "list" && (
        <section className="panel">
          <h2>Player List</h2>

          {players.length === 0 && (
            <p className="empty-state">No players available in auction list.</p>
          )}

          {players.length > 0 && (
            <div className="table-wrap">
              <table className="player-table">
                <thead>
                  <tr>
                    <th>Sr No.</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Team</th>
                    <th>Points</th>
                  </tr>
                </thead>
                <tbody>
                  {players.map((player, index) => {
                    const isCurrent = auction?.current_player?.id === player.id;
                    const statusMeta = getStatusMeta(player);

                    return (
                      <tr key={player.id} className={isCurrent ? "row-current" : ""}>
                        <td>{index + 1}</td>
                        <td>
                          {player.name}
                          {isCurrent && <span className="row-badge">Current</span>}
                        </td>
                        <td>{getRoleLabel(player.role)}</td>
                        <td>
                          <span className={`status-pill ${statusMeta.className}`}>
                            {statusMeta.text}
                          </span>
                        </td>
                        <td>{player.sold_team || "-"}</td>
                        <td>{player.sold_points ?? "-"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default App;
