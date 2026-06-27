const ISSUES_URL = "https://github.com/edonahue/Discogs_Spinner/issues";

export function Footer() {
  return (
    <footer className="app-footer" aria-label="Support">
      <span className="app-footer__text">Something not working?</span>
      <a
        className="app-footer__link"
        href={ISSUES_URL}
        target="_blank"
        rel="noreferrer"
      >
        Report a problem
      </a>
    </footer>
  );
}
