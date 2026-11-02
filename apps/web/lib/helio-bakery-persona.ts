/**
 * Maps HELIO demo identity (persona key or EMP id) → Bakery demo user_id.
 *
 * HELIO sessions expose EMP ids (e.g. northstar-EMP-0001); Bakery /auth/demo-login
 * only accepts Bakery seed ids (NS-001, …).
 */

export type BakeryPersonaMapping = {
  bakeryUserId: string;
  tenantId: "northstar";
  label: string;
};

/** Canonical HELIO → Bakery demo persona pairs (keys + EMP ids). */
export const HELIO_TO_BAKERY: Record<string, BakeryPersonaMapping> = {
  // Northstar employees
  "northstar-asha": { bakeryUserId: "NS-001", tenantId: "northstar", label: "Asha Rao" },
  "northstar-EMP-0001": { bakeryUserId: "NS-001", tenantId: "northstar", label: "Asha Rao" },
  "northstar-kiran": { bakeryUserId: "NS-005", tenantId: "northstar", label: "Kiran Desai" },
  "northstar-EMP-0005": { bakeryUserId: "NS-005", tenantId: "northstar", label: "Kiran Desai" },
  "northstar-leena": { bakeryUserId: "NS-006", tenantId: "northstar", label: "Leena Joseph" },
  "northstar-EMP-0006": { bakeryUserId: "NS-006", tenantId: "northstar", label: "Leena Joseph" },

  // Northstar IT support
  "northstar-rahul": { bakeryUserId: "NS-002", tenantId: "northstar", label: "Rahul Sharma" },
  "northstar-EMP-0002": { bakeryUserId: "NS-002", tenantId: "northstar", label: "Rahul Sharma" },
  "northstar-priya": { bakeryUserId: "NS-003", tenantId: "northstar", label: "Priya Menon" },
  "northstar-EMP-0003": { bakeryUserId: "NS-003", tenantId: "northstar", label: "Priya Menon" },
  "northstar-vikram": { bakeryUserId: "NS-004", tenantId: "northstar", label: "Vikram Rao" },
  "northstar-EMP-0004": { bakeryUserId: "NS-004", tenantId: "northstar", label: "Vikram Rao" },
  "northstar-arjun-security": {
    bakeryUserId: "NS-004",
    tenantId: "northstar",
    label: "Vikram Rao",
  },
  "northstar-EMP-0011": { bakeryUserId: "NS-004", tenantId: "northstar", label: "Vikram Rao" },
};

const BAKERY_USER_ID_RE = /^NS-\d{3}$/;

export function isBakeryUserId(id: string): boolean {
  return BAKERY_USER_ID_RE.test(id);
}

/**
 * Resolve a HELIO identity or Bakery id to a Bakery demo-login user_id.
 * Never returns HELIO EMP / persona keys (invalid for bakery demo-login).
 */
export function resolveBakeryUserId(helioOrBakeryId?: string | null): string {
  if (!helioOrBakeryId) return "NS-001";
  if (isBakeryUserId(helioOrBakeryId)) return helioOrBakeryId;

  const mapped = HELIO_TO_BAKERY[helioOrBakeryId];
  if (mapped) return mapped.bakeryUserId;

  if (helioOrBakeryId.startsWith("northstar-")) return "NS-001";

  return "NS-001";
}

export function resolveBakeryTenantId(_helioOrBakeryId?: string | null): "northstar" {
  return "northstar";
}
