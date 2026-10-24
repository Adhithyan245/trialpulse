import { useRef, useMemo, useEffect, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, RoundedBox, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { RINGS, ringForDimension, checksForClaim } from "../../checks";
import type { GateResult, Claim } from "../../types";
import type { SequenceStep } from "./useSequence";

interface Tunnel3DProps {
  draft: { claims: Claim[]; report_id: string };
  gate: GateResult;
  step: SequenceStep;
  reducedMotion: boolean;
}

// Read CSS color variables at runtime
function useCSSColor(variable: string): string {
  const [color, setColor] = useState("#808080");

  useEffect(() => {
    const updateColor = () => {
      const style = getComputedStyle(document.documentElement);
      const value = style.getPropertyValue(variable).trim();
      setColor(value || "#808080");
    };

    updateColor();

    // Re-read when theme changes
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (
          mutation.type === "attributes" &&
          mutation.attributeName === "data-theme"
        ) {
          updateColor();
        }
      }
    });

    observer.observe(document.documentElement, { attributes: true });

    return () => observer.disconnect();
  }, [variable]);

  return color;
}

interface TunnelSceneProps {
  draft: { claims: Claim[]; report_id: string };
  gate: GateResult;
  step: SequenceStep;
  reducedMotion: boolean;
  colorMuted: string;
  colorPass: string;
  colorHeld: string;
  colorAccent: string;
}

function CameraController() {
  const { camera, size } = useThree();

  useEffect(() => {
    const tunnelCenter = new THREE.Vector3(0, 0, -4.8);

    // Base camera position, pulled back ~10% from the tunnel center along the
    // view direction so the first ring ("Time") is not cut at the left edge.
    const baseAnchor = new THREE.Vector3(5.5, 2.4, 4.5);
    let basePosition = tunnelCenter
      .clone()
      .add(baseAnchor.clone().sub(tunnelCenter).multiplyScalar(1.1));

    // Scale distance if canvas is narrower than 480px
    if (size.width < 480) {
      const scale = 480 / size.width;
      basePosition = basePosition.multiplyScalar(scale);
    }

    camera.position.copy(basePosition);
    camera.lookAt(tunnelCenter);
  }, [camera, size.width]);

  return null;
}

function TunnelScene({
  draft,
  gate,
  step,
  reducedMotion,
  colorMuted,
  colorPass,
  colorHeld,
  colorAccent,
}: TunnelSceneProps) {
  // Determine which claim is traveling
  const travelingClaimIndex = step.type === "travel" ? step.claimIndex : -1;
  const travelingRingIndex = step.type === "travel" ? step.ringIndex : -1;
  const travelingClaim =
    travelingClaimIndex >= 0 ? draft.claims[travelingClaimIndex] : null;

  // Calculate z position of traveling claim (lerp from ring to ring)
  const targetZ = -travelingRingIndex * 1.6;

  // Determine stopped claims per ring
  const claimsStoppedAtRing: Record<number, string[]> = useMemo(() => {
    const result: Record<number, string[]> = {};
    if (
      step.type === "verdict" ||
      step.type === "requesting" ||
      step.type === "received" ||
      step.type === "desk"
    ) {
      for (const claim of draft.claims) {
        const claimChecks = checksForClaim(gate, claim.claim_id);
        const failedCheck = claimChecks.find((c) => !c.passed);
        if (failedCheck) {
          const ringId = ringForDimension(failedCheck.dimension);
          const ringIndex = RINGS.findIndex((r) => r.id === ringId);
          if (ringIndex >= 0) {
            if (!result[ringIndex]) result[ringIndex] = [];
            result[ringIndex].push(claim.claim_id);
          }
        }
      }
    }
    return result;
  }, [draft, gate, step]);

  return (
    <>
      <CameraController />
      
      {/* Lights */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={0.5} />

      {/* Rings */}
      {RINGS.map((ring, index) => {
        const z = -index * 1.6;

        // Determine ring color. Idle and dimmed rings use the --muted token
        // so they stay visible in both light and dark themes.
        let ringColor = colorMuted;
        let opacity = 0.8;

        if (travelingClaim && step.type === "travel") {
          const claimChecks = checksForClaim(gate, travelingClaim.claim_id);
          const checkForRing = claimChecks.find(
            (c) => ringForDimension(c.dimension) === ring.id
          );

          if (!checkForRing) {
            // No check for this claim: dim the ring
            opacity = 0.45;
          } else if (index <= travelingRingIndex) {
            // Already checked
            ringColor = checkForRing.passed ? colorPass : colorHeld;
            opacity = 1.0;
          }
        } else if (claimsStoppedAtRing[index]) {
          // After verdict: rings with stopped claims are held
          ringColor = colorHeld;
          opacity = 1.0;
        }

        return (
          <group key={ring.id} position={[0, 0, z]}>
            <mesh>
              <torusGeometry args={[1.1, 0.06, 16, 32]} />
              <meshStandardMaterial
                color={ringColor}
                transparent={opacity < 1}
                opacity={opacity}
              />
            </mesh>
            <Html
              position={[0, -1.35, 0]}
              center
              style={{
                fontSize: "11px",
                color: "var(--muted)",
                whiteSpace: "nowrap",
                pointerEvents: "none",
              }}
            >
              {ring.label}
            </Html>
          </group>
        );
      })}

      {/* Traveling claim token */}
      {travelingClaim && step.type === "travel" && (
        <ClaimToken
          claim={travelingClaim}
          targetZ={targetZ}
          reducedMotion={reducedMotion}
          gate={gate}
          travelingRingIndex={travelingRingIndex}
          colorHeld={colorHeld}
          colorAccent={colorAccent}
        />
      )}

      <OrbitControls
        enableZoom={false}
        minPolarAngle={Math.PI / 4}
        maxPolarAngle={Math.PI / 2}
        minAzimuthAngle={-Math.PI / 6}
        maxAzimuthAngle={Math.PI / 6}
        target={[0, 0, -4.8]}
      />
    </>
  );
}

interface ClaimTokenProps {
  claim: Claim;
  targetZ: number;
  reducedMotion: boolean;
  gate: GateResult;
  travelingRingIndex: number;
  colorHeld: string;
  colorAccent: string;
}

function ClaimToken({
  claim,
  targetZ,
  reducedMotion,
  gate,
  travelingRingIndex,
  colorHeld,
  colorAccent,
}: ClaimTokenProps) {
  const groupRef = useRef<THREE.Group>(null);

  // Determine if claim is stopped
  const isStopped = useMemo(() => {
    const claimChecks = checksForClaim(gate, claim.claim_id);
    const failedCheck = claimChecks.find((c) => !c.passed);
    if (!failedCheck) return false;

    const failedRingId = ringForDimension(failedCheck.dimension);
    const failedRingIndex = RINGS.findIndex((r) => r.id === failedRingId);
    return failedRingIndex === travelingRingIndex;
  }, [claim.claim_id, gate, travelingRingIndex]);

  const tokenColor = isStopped ? colorHeld : colorAccent;

  // Smooth lerp to target position
  useFrame(() => {
    if (groupRef.current) {
      if (reducedMotion) {
        groupRef.current.position.z = targetZ;
      } else {
        groupRef.current.position.z = THREE.MathUtils.lerp(
          groupRef.current.position.z,
          targetZ,
          0.08
        );
      }
    }
  });

  // Short label: only the last part (e.g., "C3")
  const shortLabel = useMemo(() => {
    const parts = claim.claim_id.split("-");
    return parts[parts.length - 1] || claim.claim_id;
  }, [claim.claim_id]);

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <RoundedBox args={[0.4, 0.25, 0.15]} radius={0.05} smoothness={4}>
        <meshStandardMaterial color={tokenColor} />
      </RoundedBox>
      <Html
        position={[0, 0.2, 0]}
        center
        style={{
          fontSize: "10px",
          fontFamily: "IBM Plex Mono, monospace",
          fontWeight: "500",
          color: "var(--text)",
          whiteSpace: "nowrap",
          pointerEvents: "none",
        }}
      >
        {shortLabel}
      </Html>
    </group>
  );
}

export function Tunnel3D({
  draft,
  gate,
  step,
  reducedMotion,
}: Tunnel3DProps) {
  const colorMuted = useCSSColor("--muted");
  const colorPass = useCSSColor("--pass");
  const colorHeld = useCSSColor("--held");
  const colorAccent = useCSSColor("--accent");

  return (
    <div style={{ height: "360px", width: "100%" }}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [6.05, 2.64, 5.43], fov: 38 }}
        gl={{ alpha: true }}
        style={{ background: "transparent" }}
      >
        <TunnelScene
          draft={draft}
          gate={gate}
          step={step}
          reducedMotion={reducedMotion}
          colorMuted={colorMuted}
          colorPass={colorPass}
          colorHeld={colorHeld}
          colorAccent={colorAccent}
        />
      </Canvas>
    </div>
  );
}

export default Tunnel3D;
