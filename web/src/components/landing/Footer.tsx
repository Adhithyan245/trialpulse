export function Footer() {
  return (
    <footer className="mt-16 border-t border-line pt-8 text-sm text-muted">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <h3 className="font-medium text-text">Data sources</h3>
          <ul className="mt-2 space-y-1">
            <li>ClinicalTrials.gov</li>
            <li>MassGIS</li>
            <li>CDC PLACES</li>
            <li>CMS</li>
            <li>US Census Bureau</li>
          </ul>
        </div>

        <div className="space-y-2">
          <p>
            Reliability checks by{" "}
            <a
              href="https://github.com/Adhithyan245/PulseEval"
              className="text-accent hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              PulseEval
            </a>{" "}
            (MIT)
          </p>
          <p>
            Built with{" "}
            <a
              href="https://kiro.dev"
              className="text-accent hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Kiro
            </a>
          </p>
          <p>
            <a
              href="https://github.com/Adhithyan245/trialpulse"
              className="text-accent hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              View on GitHub
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
