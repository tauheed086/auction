import leagueLogo from "../../league_logo-removebg-preview.png";

function LeagueBrand() {
  return (
    <section className="league-brand" aria-label="League branding">
      <img src={leagueLogo} alt="16 No. Premiere League Logo" className="league-logo" />
      <h1 className="league-name">16 No. Premiere League</h1>
    </section>
  );
}

export default LeagueBrand;
