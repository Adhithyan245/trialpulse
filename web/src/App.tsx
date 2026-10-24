import { useEffect, useState } from "react";
import { Shell } from "./components/Shell";
import { Landing } from "./components/Landing";
import { Scene1Trial } from "./scenes/Scene1Trial";
import { Scene2Checkpoint } from "./scenes/Scene2Checkpoint";
import { Scene3Seal } from "./scenes/Scene3Seal";
import { Scene4Verified } from "./scenes/Scene4Verified";
import { Scene5Proof } from "./scenes/Scene5Proof";

function useHashRoute(): string {
  const [hash, setHash] = useState(() => window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const hash = useHashRoute();

  if (hash === "#/" || hash === "") {
    return (
      <Shell>
        <Landing />
      </Shell>
    );
  }

  let scene;
  switch (hash) {
    case "#/trial":
      scene = <Scene1Trial />;
      break;
    case "#/checkpoint":
      scene = <Scene2Checkpoint />;
      break;
    case "#/seal":
      scene = <Scene3Seal />;
      break;
    case "#/verified":
      scene = <Scene4Verified />;
      break;
    case "#/proof":
      scene = <Scene5Proof />;
      break;
    default:
      scene = <Landing />;
  }

  return <Shell>{scene}</Shell>;
}
