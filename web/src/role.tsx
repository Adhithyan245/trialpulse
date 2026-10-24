import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import type { Role } from "./types";

const STORAGE_KEY = "trialpulse.role";
const DEFAULT_ROLE: Role = "monitor";
const VALID_ROLES: Role[] = ["monitor", "coordinator", "safety_reviewer"];

// Module-level mirror of the current role so the plain fetch client in api.ts
// can read it without a hook.
let currentRole: Role = DEFAULT_ROLE;

export function getRole(): Role {
  return currentRole;
}

function readStored(): Role {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && (VALID_ROLES as string[]).includes(raw)) {
      return raw as Role;
    }
  } catch {
    // localStorage may be unavailable; fall back to the default.
  }
  return DEFAULT_ROLE;
}

function writeStored(role: Role): void {
  try {
    localStorage.setItem(STORAGE_KEY, role);
  } catch {
    // ignore storage failures
  }
}

interface RoleContextValue {
  role: Role;
  setRole: (role: Role) => void;
}

const RoleContext = createContext<RoleContextValue | null>(null);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(() => {
    const initial = readStored();
    currentRole = initial;
    return initial;
  });

  const setRole = useCallback((next: Role) => {
    currentRole = next;
    writeStored(next);
    setRoleState(next);
  }, []);

  return (
    <RoleContext.Provider value={{ role, setRole }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (ctx === null) {
    throw new Error("useRole must be used within a RoleProvider");
  }
  return ctx;
}
