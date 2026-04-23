import { useEffect, useRef, useState } from "react";
import { getCurrentAuction, getPlayers } from "./api";
import PlayerCard from "./components/PlayerCard";
import Confetti from "react-confetti";
import { fireCelebration } from "./utils/celebration";

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
  const [confetti, setConfetti] = useState(false);
  const previousStatusRef = useRef({ playerId: null, isSold: false });
  const confettiTimerRef = useRef(null);

  const triggerConfetti = () => {
    setConfetti(true);
    clearTimeout(confettiTimerRef.current);
    confettiTimerRef.current = setTimeout(() => setConfetti(false), 5000);
  };

  const fetchViewerData = async () => {
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
  };

  useEffect(() => {
    fetchViewerData();
    const intervalId = setInterval(fetchViewerData, 2000);

    return () => {
      clearInterval(intervalId);
      clearTimeout(confettiTimerRef.current);
    };
  }, []);

  const currentPlayer = auction?.current_player;

  return (
    <div className="page">
      {confetti && <Confetti recycle={false} numberOfPieces={520} />}

      <div className="top-links">
        <a href="/">Viewer Board</a>
        <a href="/admin-board">Admin Board</a>
      </div>

      <h1>Player Auction Viewer</h1>

      {!currentPlayer && (
        <p className="empty-state">Waiting for admin to select a player.</p>
      )}

      {currentPlayer && (
        <div className="viewer-card-wrap">
          <PlayerCard player={currentPlayer} />
        </div>
      )}

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
    </div>
  );
}

export default App;
