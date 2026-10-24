import { useEffect, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { ClockParticipant, Site } from "../../types";

interface CountyFeature extends Feature {
  properties: {
    county: string;
    fips: string;
  };
}

interface MapViewProps {
  sites: Site[];
  participants: ClockParticipant[];
  selectedParticipantId: string | null;
  onSelectParticipant: (pid: string) => void;
  prefersReducedMotion: boolean;
}

const SITE_ANCHORS: Record<string, [number, number]> = {
  S01: [-71.06, 42.36], // Boston
  S02: [-71.8, 42.26], // Worcester
  S03: [-72.59, 42.1], // Springfield
};

const SITE_COUNTIES: Record<string, string> = {
  S01: "Suffolk",
  S02: "Worcester",
  S03: "Hampden",
};

export function MapView({
  sites,
  participants,
  selectedParticipantId,
  onSelectParticipant,
  prefersReducedMotion,
}: MapViewProps) {
  const [geoData, setGeoData] = useState<FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/ma-counties.geojson")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load county boundaries");
        return res.json();
      })
      .then((data) => setGeoData(data as FeatureCollection))
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return <div className="text-sm text-held">{error}</div>;
  }

  if (!geoData) {
    return <div className="text-sm text-muted">Loading map...</div>;
  }

  const width = 800;
  const height = 600;
  const padding = 16;

  const projection = geoMercator().fitExtent(
    [[padding, padding], [width - padding, height - padding]],
    geoData
  );
  const pathGenerator = geoPath().projection(projection);

  // Group participants by site
  const participantsBySite: Record<string, ClockParticipant[]> = {};
  participants.forEach((p) => {
    if (!participantsBySite[p.site_id]) {
      participantsBySite[p.site_id] = [];
    }
    participantsBySite[p.site_id].push(p);
  });

  // Generate participant positions: offsets in SCREEN pixels after projecting
  // the site anchor. Ring 1: 6 dots at 12px radius, Ring 2: 12 dots at 24px,
  // Ring 3: rest at 36px. Angle evenly spaced, starting at -90deg.
  const participantPositions = participants.map((p) => {
    const anchor = SITE_ANCHORS[p.site_id];
    if (!anchor) return { participant: p, x: 0, y: 0 };

    const anchorCoords = projection(anchor);
    const anchorX = anchorCoords?.[0] ?? 0;
    const anchorY = anchorCoords?.[1] ?? 0;

    const siteParticipants = participantsBySite[p.site_id] || [];
    const indexInSite = siteParticipants.indexOf(p);

    if (indexInSite === 0) {
      return { participant: p, x: anchorX, y: anchorY };
    }

    // Determine ring and position
    const ring1Size = 6;
    const ring2Size = 12;
    let ring = 1;
    let posInRing = indexInSite - 1;

    if (posInRing >= ring1Size) {
      if (posInRing < ring1Size + ring2Size) {
        ring = 2;
        posInRing -= ring1Size;
      } else {
        ring = 3;
        posInRing -= ring1Size + ring2Size;
      }
    }

    const radiusPx = ring === 1 ? 12 : ring === 2 ? 24 : 36;
    const pointsInRing = ring === 1 ? ring1Size : ring === 2 ? ring2Size : Math.max(1, siteParticipants.length - ring1Size - ring2Size);
    const angle = -Math.PI / 2 + (posInRing / pointsInRing) * 2 * Math.PI; // Start at -90deg

    const x = anchorX + radiusPx * Math.cos(angle);
    const y = anchorY + radiusPx * Math.sin(angle);

    return { participant: p, x, y };
  });

  // Site label positions: to the right of the outer ring
  const siteLabelPositions = sites.map((site) => {
    const anchor = SITE_ANCHORS[site.site_id];
    if (!anchor) return null;
    const coords = projection(anchor);
    const count = participantsBySite[site.site_id]?.length ?? 0;
    
    // Determine outer ring radius based on participant count
    const ring1Size = 6;
    const ring2Size = 12;
    let outerRadius = 12; // Default to ring 1
    if (count > 1 + ring1Size + ring2Size) {
      outerRadius = 36; // Ring 3
    } else if (count > 1 + ring1Size) {
      outerRadius = 24; // Ring 2
    } else if (count > 1) {
      outerRadius = 12; // Ring 1
    } else {
      outerRadius = 0; // Single participant
    }

    return {
      site,
      x: (coords?.[0] ?? 0) + outerRadius + 10, // To the right of outer ring
      y: (coords?.[1] ?? 0),
      count,
    };
  });

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ height: "auto" }}
        className="border border-line rounded bg-card"
        role="img"
        aria-label="Massachusetts trial map with participant locations"
      >
        {/* County boundaries */}
        {geoData.features.map((feature: Feature<Geometry>) => {
          const countyFeature = feature as CountyFeature;
          const d = pathGenerator(feature);
          const isSiteCounty = Object.values(SITE_COUNTIES).includes(
            countyFeature.properties.county
          );

          return (
            <g key={countyFeature.properties.fips}>
              <path
                d={d || ""}
                fill="var(--card)"
                stroke="var(--muted)"
                strokeOpacity={isSiteCounty ? 1 : 0.55}
                strokeWidth="1"
              />
              {isSiteCounty && (
                <text
                  x={
                    pathGenerator.centroid(feature)[0] ||
                    width / 2
                  }
                  y={
                    pathGenerator.centroid(feature)[1] ||
                    height / 2
                  }
                  textAnchor="middle"
                  fontSize="10"
                  fill="var(--muted)"
                  className="pointer-events-none"
                >
                  {countyFeature.properties.county}
                </text>
              )}
            </g>
          );
        })}

        {/* Site labels */}
        {siteLabelPositions.map((pos) => {
          if (!pos) return null;
          return (
            <text
              key={pos.site.site_id}
              x={pos.x}
              y={pos.y}
              fontSize="12"
              fill="var(--text)"
              fontWeight="600"
              className="pointer-events-none"
            >
              {pos.site.city} ({pos.count}{" "}
              {pos.count === 1 ? "participant" : "participants"})
            </text>
          );
        })}

        {/* Participant dots */}
        {participantPositions.map(({ participant, x, y }) => {
          const isSelected = participant.participant_id === selectedParticipantId;
          const hasHalo = participant.drift;
          const isHollow = !participant.worn || participant.non_wear;
          const hasTick = participant.diary_conflict;

          // Pulse animation period (if resting_hr is present and motion is not reduced)
          const pulsePeriod =
            participant.resting_hr && !prefersReducedMotion
              ? 60 / participant.resting_hr
              : 0;

          const siteForParticipant = sites.find(
            (s) => s.site_id === participant.site_id
          );
          const siteName = siteForParticipant?.city || participant.site_id;

          let stateLabel = "";
          if (participant.drift) stateLabel = "drift detected";
          else if (!participant.worn) stateLabel = "not worn";
          else if (participant.non_wear) stateLabel = "non-wear";
          if (participant.diary_conflict)
            stateLabel = stateLabel
              ? `${stateLabel}, diary conflict`
              : "diary conflict";

          const ariaLabel = `${participant.participant_id}, ${siteName}${stateLabel ? `, ${stateLabel}` : ""}`;

          return (
            <g key={participant.participant_id}>
              {/* Halo for drift */}
              {hasHalo && (
                <circle
                  cx={x}
                  cy={y}
                  r="7"
                  fill="none"
                  stroke="var(--watch)"
                  strokeWidth="2"
                  opacity="0.7"
                />
              )}

              {/* Main dot */}
              <circle
                cx={x}
                cy={y}
                r="4.5"
                fill={isHollow ? "none" : "var(--accent)"}
                stroke="var(--accent)"
                strokeWidth="1.5"
                opacity={isHollow ? 0.4 : 1}
                className="cursor-pointer transition-all hover:r-5"
                style={
                  pulsePeriod > 0
                    ? {
                        animation: `pulse ${pulsePeriod}s ease-in-out infinite`,
                      }
                    : undefined
                }
                tabIndex={0}
                role="button"
                aria-label={ariaLabel}
                onClick={() => onSelectParticipant(participant.participant_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectParticipant(participant.participant_id);
                  }
                }}
              />

              {/* Selection indicator */}
              {isSelected && (
                <circle
                  cx={x}
                  cy={y}
                  r="8"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="2"
                  strokeDasharray="2,2"
                />
              )}

              {/* Diary conflict tick */}
              {hasTick && (
                <path
                  d={`M ${x + 3} ${y - 5} l 2 3 l 4 -6`}
                  fill="none"
                  stroke="var(--text)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="pointer-events-none"
                />
              )}
            </g>
          );
        })}
      </svg>

      {/* Attribution */}
      <p className="text-xs text-muted mt-1">
        County boundaries: U.S. Census Bureau
      </p>

      <style>{`
        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.15);
            opacity: 0.8;
          }
        }
      `}</style>
    </div>
  );
}
