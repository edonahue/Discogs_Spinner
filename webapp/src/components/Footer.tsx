import { DISCOGS_ATTRIBUTION_TEXT, DISCOGS_NOTICE, DISCOGS_URL, ISSUES_URL } from "../brand";

export function Footer() {
  return (
    <footer className="app-footer" aria-label="Support">
      <span className="app-footer__text">{DISCOGS_NOTICE}</span>
      <a className="app-footer__link" href={DISCOGS_URL} target="_blank" rel="noreferrer">
        {DISCOGS_ATTRIBUTION_TEXT}
      </a>
      <span className="app-footer__text">Something not working?</span>
      <a className="app-footer__link" href={ISSUES_URL} target="_blank" rel="noreferrer">
        Report a problem
      </a>
    </footer>
  );
}
