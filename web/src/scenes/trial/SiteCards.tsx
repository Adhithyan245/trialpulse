import { CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";
import type { ClockParticipant, Site } from "../../types";

interface SiteCardsProps {
  sites: Site[];
  participants: ClockParticipant[];
}

export function SiteCards({ sites, participants }: SiteCardsProps) {
  // Group participants by site
  const participantsBySite: Record<string, ClockParticipant[]> = {};
  participants.forEach((p) => {
    if (!participantsBySite[p.site_id]) {
      participantsBySite[p.site_id] = [];
    }
    participantsBySite[p.site_id].push(p);
  });

  return (
    <div className="grid gap-3">
      {sites.map((site) => {
        const siteParticipants = participantsBySite[site.site_id] || [];
        const wornCount = siteParticipants.filter((p) => p.worn).length;
        const driftCount = siteParticipants.filter((p) => p.drift).length;
        const nonWearCount = siteParticipants.filter((p) => p.non_wear).length;

        // Determine overall status
        let status: "pass" | "watch" | "held" = "pass";
        if (nonWearCount > 0) status = "held";
        else if (driftCount > 0) status = "watch";

        const statusConfig = {
          pass: {
            Icon: CheckCircle2,
            bg: "bg-pass-soft",
            fg: "text-pass",
          },
          watch: {
            Icon: AlertTriangle,
            bg: "bg-watch-soft",
            fg: "text-watch",
          },
          held: {
            Icon: ShieldAlert,
            bg: "bg-held-soft",
            fg: "text-held",
          },
        };

        const { Icon, bg, fg } = statusConfig[status];

        return (
          <div
            key={site.site_id}
            className={`p-3 rounded border border-line ${bg}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="font-semibold text-text">
                  {site.site_id} {site.city}
                </div>
                <div className="text-xs text-muted">{site.county} County</div>
              </div>
              <Icon className={`h-5 w-5 ${fg}`} />
            </div>

            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted">Worn today:</span>
                <span className="font-mono tabular-nums">
                  {wornCount} of {siteParticipants.length}
                </span>
              </div>

              {driftCount > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-watch">Drift detected:</span>
                  <span className="font-mono tabular-nums text-watch">
                    {driftCount}
                  </span>
                </div>
              )}

              {nonWearCount > 0 && (
                <div className="flex items-center justify-between">
                  <span className="text-held">Non-wear:</span>
                  <span className="font-mono tabular-nums text-held">
                    {nonWearCount}
                  </span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
