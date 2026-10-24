import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import { trial, clock, metrics } from "../api";
import type { Trial, Clock, Metrics } from "../types";
import { MapView } from "./trial/MapView";
import { TrialClock } from "./trial/TrialClock";
import { Legend } from "./trial/Legend";
import { SiteCards } from "./trial/SiteCards";
import { ParticipantDetails } from "./trial/ParticipantDetails";

export function Scene1Trial() {
  const [trialData, setTrialData] = useState<Trial | null>(null);
  const [clockData, setClockData] = useState<Clock | null>(null);
  const [metricsData, setMetricsData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currentDay, setCurrentDay] = useState(15);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<1 | 2>(1);
  const [selectedParticipantId, setSelectedParticipantId] = useState<string | null>("P-07");

  const prefersReducedMotion = useReducedMotion();

  // Load initial data
  useEffect(() => {
    let active = true;

    Promise.all([trial(), clock(), metrics()])
      .then(([trialResp, clockResp, metricsResp]) => {
        if (!active) return;
        setTrialData(trialResp);
        setClockData(clockResp);
        setMetricsData(metricsResp);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.message);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  // Play/pause animation
  useEffect(() => {
    if (!playing || !trialData) return;

    const interval = setInterval(
      () => {
        setCurrentDay((prev) => {
          if (prev >= trialData.days) {
            setPlaying(false);
            return trialData.days;
          }
          return prev + 1;
        });
      },
      speed === 1 ? 2100 : 1050
    );

    return () => clearInterval(interval);
  }, [playing, speed, trialData]);

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="text-lg text-muted">Loading trial data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="text-lg text-held">{error}</div>
      </div>
    );
  }

  if (!trialData || !clockData || !metricsData) {
    return (
      <div className="p-8 text-center">
        <div className="text-lg text-muted">No data available</div>
      </div>
    );
  }

  const currentDayData = clockData.days.find((d) => d.day === currentDay);
  const currentParticipants = currentDayData?.participants || [];

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      {/* Synthetic data ribbon */}
      <div className="mb-6 p-3 bg-watch-soft border border-watch text-watch rounded text-center font-medium">
        Synthetic data
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        <h1 className="text-3xl font-semibold text-text">
          Scene 1: The trial, alive
        </h1>

        {/* Trial clock */}
        <TrialClock
          currentDay={currentDay}
          totalDays={trialData.days}
          doseStartDay={trialData.dose_start_day}
          playing={playing}
          speed={speed}
          onDayChange={setCurrentDay}
          onTogglePlay={() => setPlaying(!playing)}
          onToggleSpeed={() => setSpeed(speed === 1 ? 2 : 1)}
        />

        {/* Main layout: map + right panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map section (2 columns on large screens) */}
          <div className="lg:col-span-2 space-y-4">
            <MapView
              sites={trialData.sites}
              participants={currentParticipants}
              selectedParticipantId={selectedParticipantId}
              onSelectParticipant={setSelectedParticipantId}
              prefersReducedMotion={prefersReducedMotion ?? false}
            />
            <Legend />
          </div>

          {/* Right panel (1 column on large screens, stacks below on smaller) */}
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold mb-3">Site Status</h2>
              <SiteCards
                sites={trialData.sites}
                participants={currentParticipants}
              />
            </div>

            {selectedParticipantId && (
              <div>
                <h2 className="text-lg font-semibold mb-3">
                  Participant Details
                </h2>
                <ParticipantDetails
                  participantId={selectedParticipantId}
                  sites={trialData.sites}
                  currentDay={currentDay}
                  doseStartDay={trialData.dose_start_day}
                  publicMetrics={metricsData.public}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
