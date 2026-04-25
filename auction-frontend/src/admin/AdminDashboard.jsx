import { useEffect, useMemo, useRef, useState } from "react";
import Confetti from "react-confetti";
import {
  adminLogin,
  adminLogout,
  adminMe,
  clearAdminToken,
  createPlayer,
  getCurrentAuction,
  getPlayers,
  getTeams,
  hasAdminToken,
  setInitialTeamPurse,
  sellCurrentPlayer,
  setAdminToken,
  setAuctionPlayer,
  syncTeams,
  skipCurrentPlayer,
} from "../api";
import PlayerCard from "../components/PlayerCard";
import LeagueBrand from "../components/LeagueBrand";
import { TEAM_OPTIONS } from "../constants/teams";

function getRoleLabel(role) {
  const labels = {
    batsman: "Batsman",
    bowler: "Bowler",
    allrounder: "All-Rounder",
  };
  return labels[role] || role;
}

function AdminDashboard() {
  const [players, setPlayers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [auction, setAuction] = useState(null);
  const [confetti, setConfetti] = useState(false);
  const [isAuthChecking, setIsAuthChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authUser, setAuthUser] = useState("");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [formState, setFormState] = useState({
    name: "",
    role: "batsman",
    image: null,
  });
  const [sellForm, setSellForm] = useState({
    soldTeam: "",
    soldPoints: "",
  });
  const [sellError, setSellError] = useState("");
  const [teamError, setTeamError] = useState("");
  const [initialPurseInput, setInitialPurseInput] = useState("");
  const [isSettingPurse, setIsSettingPurse] = useState(false);
  const [playerSelectionError, setPlayerSelectionError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const confettiTimerRef = useRef(null);

  const fetchData = async () => {
    try {
      const [playersRes, auctionRes, teamsRes] = await Promise.all([
        getPlayers(),
        getCurrentAuction(),
        getTeams(),
      ]);
      setPlayers(playersRes.data);
      setAuction(auctionRes.data);
      setTeams(teamsRes.data);
      setInitialPurseInput(
        auctionRes.data?.team_purse_limit === null ||
          auctionRes.data?.team_purse_limit === undefined
          ? ""
          : String(auctionRes.data.team_purse_limit)
      );
    } catch (error) {
      console.error("Failed to fetch admin data", error);
    }
  };

  useEffect(() => {
    const verifyAuth = async () => {
      if (!hasAdminToken()) {
        setIsAuthChecking(false);
        return;
      }

      try {
        const meRes = await adminMe();
        if (meRes.data?.is_staff) {
          setIsAuthenticated(true);
          setAuthUser(meRes.data.username || "");
        } else {
          clearAdminToken();
        }
      } catch {
        clearAdminToken();
      } finally {
        setIsAuthChecking(false);
      }
    };

    verifyAuth();
    return () => clearTimeout(confettiTimerRef.current);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const bootstrapData = async () => {
      try {
        await syncTeams(TEAM_OPTIONS);
      } catch (error) {
        console.error("Failed to sync teams", error);
      }
      await fetchData();
    };

    bootstrapData();
  }, [isAuthenticated]);

  const triggerConfetti = () => {
    setConfetti(true);
    clearTimeout(confettiTimerRef.current);
    confettiTimerRef.current = setTimeout(() => setConfetti(false), 5000);
  };

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormState((prev) => ({ ...prev, [name]: value }));
  };

  const handleLoginInput = (event) => {
    const { name, value } = event.target;
    setLoginForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    if (!loginForm.username || !loginForm.password) {
      setLoginError("Username and password are required.");
      return;
    }

    setIsLoggingIn(true);
    try {
      const res = await adminLogin({
        username: loginForm.username,
        password: loginForm.password,
      });
      setAdminToken(res.data.token);
      setIsAuthenticated(true);
      setAuthUser(res.data.username || loginForm.username);
      setLoginError("");
    } catch (error) {
      setLoginError(error?.response?.data?.detail || "Login failed.");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = async () => {
    try {
      await adminLogout();
    } catch {
      // Token can be invalid or expired; clear local auth state anyway.
    } finally {
      clearAdminToken();
      setIsAuthenticated(false);
      setAuthUser("");
      setPlayers([]);
      setTeams([]);
      setAuction(null);
      setSellError("");
      setTeamError("");
      setPlayerSelectionError("");
      setInitialPurseInput("");
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setFormState((prev) => ({ ...prev, image: file }));
  };

  const handleCreatePlayer = async (event) => {
    event.preventDefault();
    if (!formState.name || !formState.role || !formState.image) {
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("name", formState.name);
      formData.append("role", formState.role);
      formData.append("image", formState.image);

      await createPlayer(formData);
      setFormState({ name: "", role: "batsman", image: null });
      await fetchData();
    } catch (error) {
      console.error("Failed to create player", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSetPlayer = async (playerId) => {
    if (!auction?.id) {
      return;
    }

    try {
      setPlayerSelectionError("");
      await setAuctionPlayer(auction.id, playerId);
      await fetchData();
    } catch (error) {
      console.error("Failed to set auction player", error);
      setPlayerSelectionError(
        error?.response?.data?.detail || "Failed to select player."
      );
    }
  };

  const handleSellPlayer = async () => {
    if (!auction?.id) {
      return;
    }

    if (!sellForm.soldTeam) {
      setSellError("Select the team before selling the player.");
      return;
    }
    if (!teams.find((team) => team.name === sellForm.soldTeam)) {
      setSellError("Selected team is not configured. Set team purse first.");
      return;
    }

    const points = Number(sellForm.soldPoints);
    if (!Number.isFinite(points) || points <= 0) {
      setSellError("Enter valid points greater than 0.");
      return;
    }

    try {
      setSellError("");
      await sellCurrentPlayer(auction.id, {
        sold_team: sellForm.soldTeam,
        sold_points: points,
      });
      triggerConfetti();
      await fetchData();
    } catch (error) {
      console.error("Failed to sell player", error);
      setSellError(
        error?.response?.data?.detail || "Failed to sell player. Check values."
      );
    }
  };

  const handleSkipPlayer = async () => {
    if (!auction?.id) {
      return;
    }

    try {
      await skipCurrentPlayer(auction.id);
      await fetchData();
    } catch (error) {
      console.error("Failed to skip player", error);
    }
  };

  const handleSetInitialPurse = async () => {
    const purse = Number(initialPurseInput);
    if (!Number.isFinite(purse) || purse <= 0 || !Number.isInteger(purse)) {
      setTeamError("Initial purse must be a whole number greater than 0.");
      return;
    }

    setIsSettingPurse(true);
    try {
      setTeamError("");
      await setInitialTeamPurse(purse);
      await fetchData();
    } catch (error) {
      setTeamError(
        error?.response?.data?.detail || "Failed to set initial purse."
      );
    } finally {
      setIsSettingPurse(false);
    }
  };

  const filteredPlayers = useMemo(() => {
    if (statusFilter === "sold") {
      return players.filter((player) => player.is_sold);
    }
    if (statusFilter === "skipped") {
      return players.filter((player) => player.is_skipped && !player.is_sold);
    }
    if (statusFilter === "none") {
      return players.filter((player) => !player.is_sold && !player.is_skipped);
    }
    return players;
  }, [players, statusFilter]);
  const navigablePlayers = useMemo(() => filteredPlayers, [filteredPlayers]);

  const currentPlayer = auction?.current_player || null;
  const currentPlayerIndex = useMemo(() => {
    if (!currentPlayer) {
      return -1;
    }
    return navigablePlayers.findIndex((player) => player.id === currentPlayer.id);
  }, [navigablePlayers, currentPlayer]);

  const isPrevDisabled =
    navigablePlayers.length === 0 || currentPlayerIndex === 0;
  const isNextDisabled =
    navigablePlayers.length === 0 ||
    currentPlayerIndex === navigablePlayers.length - 1;

  const handleSelectByOffset = async (offset) => {
    if (!auction?.id || navigablePlayers.length === 0) {
      return;
    }

    let targetIndex;
    if (currentPlayerIndex === -1) {
      targetIndex = offset > 0 ? 0 : navigablePlayers.length - 1;
    } else {
      targetIndex = currentPlayerIndex + offset;
    }

    if (targetIndex < 0 || targetIndex >= navigablePlayers.length) {
      return;
    }

    await handleSetPlayer(navigablePlayers[targetIndex].id);
  };

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (!currentPlayer) {
      setSellForm({ soldTeam: "", soldPoints: "" });
      return;
    }

    setSellForm({
      soldTeam: currentPlayer.sold_team || "",
      soldPoints:
        currentPlayer.sold_points === null || currentPlayer.sold_points === undefined
          ? ""
          : String(currentPlayer.sold_points),
    });
    setSellError("");
  }, [
    isAuthenticated,
    currentPlayer?.id,
    currentPlayer?.sold_team,
    currentPlayer?.sold_points,
  ]);

  if (isAuthChecking) {
    return (
      <div className="page">
        <div className="top-links">
          <a href="/">Viewer Board</a>
          <a href="/admin-board">Admin Board</a>
        </div>
        <section className="panel auth-panel">
          <h2>Checking admin session...</h2>
        </section>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="page">
        <div className="top-links">
          <a href="/">Viewer Board</a>
          <a href="/admin-board">Admin Board</a>
        </div>

        <h1>Admin Login</h1>
        <section className="panel auth-panel">
          <h2>Sign in to Admin Dashboard</h2>
          <form className="auth-form" onSubmit={handleLogin}>
            <input
              type="text"
              name="username"
              placeholder="Username"
              value={loginForm.username}
              onChange={handleLoginInput}
              required
            />
            <input
              type="password"
              name="password"
              placeholder="Password"
              value={loginForm.password}
              onChange={handleLoginInput}
              required
            />
            <button type="submit" disabled={isLoggingIn}>
              {isLoggingIn ? "Signing In..." : "Login"}
            </button>
          </form>
          {loginError && <p className="sell-error">{loginError}</p>}
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      {confetti && <Confetti recycle={false} numberOfPieces={520} />}

      <div className="top-links">
        <a href="/">Viewer Board</a>
        <a href="/admin-board">Admin Board</a>
        <button type="button" className="secondary" onClick={handleLogout}>
          Logout ({authUser})
        </button>
      </div>

      <LeagueBrand />

      <section className="panel">
        <h2>Add Player</h2>
        <form className="add-player-form" onSubmit={handleCreatePlayer}>
          <input
            type="text"
            name="name"
            placeholder="Player name"
            value={formState.name}
            onChange={handleInputChange}
            required
          />
          <select
            name="role"
            value={formState.role}
            onChange={handleInputChange}
            required
          >
            <option value="batsman">Batsman</option>
            <option value="bowler">Bowler</option>
            <option value="allrounder">All-Rounder</option>
          </select>
          <input type="file" accept="image/*" onChange={handleFileChange} required />
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Adding..." : "Add Player"}
          </button>
        </form>
      </section>

      {auction?.team_purse_limit == null && (
        <section className="panel">
          <h2>Initial Team Purse</h2>
          <p>
            Set one purse amount for all teams before starting auction. After first
            player selection, purse is locked.
          </p>
          <div className="control-row">
            <input
              type="number"
              min="1"
              step="1"
              placeholder="Enter purse amount"
              value={initialPurseInput}
              onChange={(event) => setInitialPurseInput(event.target.value)}
              disabled={Boolean(auction?.is_purse_locked)}
            />
            <button
              type="button"
              onClick={handleSetInitialPurse}
              disabled={Boolean(auction?.is_purse_locked) || isSettingPurse}
            >
              {isSettingPurse ? "Setting..." : "Start Auction"}
            </button>
          </div>
          {teamError && <p className="sell-error">{teamError}</p>}
        </section>
      )}

      <section className="panel">
        <h2>Current Auction Player</h2>
        {!currentPlayer && (
          <p className="empty-state">Select a player to begin auction control.</p>
        )}

        {currentPlayer && (
          <>
            <div className="current-player-nav-wrap">
              <button
                className="nav-arrow left"
                onClick={() => handleSelectByOffset(-1)}
                disabled={isPrevDisabled}
                aria-label="Previous player"
              >
                {"<"}
              </button>

              <div className="viewer-card-wrap">
                <PlayerCard player={currentPlayer} />
              </div>

              <button
                className="nav-arrow right"
                onClick={() => handleSelectByOffset(1)}
                disabled={isNextDisabled}
                aria-label="Next player"
              >
                {">"}
              </button>
            </div>
            <div className="control-row">
              <div className="sell-controls">
                <select
                  value={sellForm.soldTeam}
                  onChange={(event) =>
                    setSellForm((prev) => ({ ...prev, soldTeam: event.target.value }))
                  }
                >
                  <option value="">Select Team</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.name}>
                      {team.name} ({team.balance_points ?? 0} left)
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="1"
                  placeholder="Points"
                  value={sellForm.soldPoints}
                  onChange={(event) =>
                    setSellForm((prev) => ({ ...prev, soldPoints: event.target.value }))
                  }
                />
                <button onClick={handleSellPlayer}>Sell</button>
              </div>
              <button className="secondary" onClick={handleSkipPlayer}>
                Skip
              </button>
            </div>
            {teams.length === 0 && (
              <p className="sell-error">
                No team configured. Sync teams and set initial purse first.
              </p>
            )}
            {sellError && <p className="sell-error">{sellError}</p>}
          </>
        )}
      </section>

      <section className="panel">
        <details className="expense-dropdown">
          <summary className="expense-summary">
            Team Expense List ({teams.length})
          </summary>

          <div className="expense-content">
            {teams.length === 0 && (
              <p className="empty-state">
                No teams found. Refresh page to sync default teams.
              </p>
            )}

            {teams.length > 0 && (
              <div className="table-wrap">
                <table className="player-table">
                  <thead>
                    <tr>
                      <th>Team Name</th>
                      <th>Players Bought</th>
                      <th>Point Spend</th>
                      <th>Point Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teams.map((team) => (
                      <tr key={team.id}>
                        <td>{team.name}</td>
                        <td>
                          {team.players_bought?.length
                            ? team.players_bought.join(", ")
                            : "-"}
                        </td>
                        <td>{team.spent_points ?? 0}</td>
                        <td>{team.balance_points ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </details>
      </section>

      <section className="panel">
        <h2>Select Player</h2>
        {playerSelectionError && <p className="sell-error">{playerSelectionError}</p>}
        {players.length === 0 && (
          <p className="empty-state">No players added yet.</p>
        )}

        {players.length > 0 && (
          <div>
            <div className="table-toolbar">
              <label htmlFor="status-filter">Status Filter</label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="all">All</option>
                <option value="sold">Sold</option>
                <option value="skipped">Skipped</option>
                <option value="none">Not Sold/Skipped</option>
              </select>
            </div>

            {filteredPlayers.length === 0 && (
              <p className="empty-state">
                No players found for selected status filter.
              </p>
            )}

            {filteredPlayers.length > 0 && (
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
                    {filteredPlayers.map((player, index) => {
                      const isCurrent = auction?.current_player?.id === player.id;
                      const isSold = player.is_sold;
                      const isSkipped = player.is_skipped;
                      const statusText = isSold
                        ? "Sold"
                        : isSkipped
                          ? "Skipped"
                          : "Available";
                      const statusClass = isSold
                        ? "status-sold"
                        : isSkipped
                          ? "status-skipped"
                          : "status-available";

                      return (
                        <tr
                          key={player.id}
                          className={`${isCurrent ? "row-current" : ""} ${
                            isSold ? "row-sold" : "row-clickable"
                          }`}
                          onClick={() => handleSetPlayer(player.id)}
                        >
                          <td>{index + 1}</td>
                          <td>
                            {player.name}
                            {isCurrent && <span className="row-badge">Current</span>}
                          </td>
                          <td>{getRoleLabel(player.role)}</td>
                          <td>
                            <span className={`status-pill ${statusClass}`}>
                              {statusText}
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
          </div>
        )}
      </section>
    </div>
  );
}

export default AdminDashboard;
