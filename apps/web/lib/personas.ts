export type PersonaSection = "employees" | "it_support";

export interface Persona {
  key: string;
  name: string;
  role: string;
  tenant: "northstar";
  section: PersonaSection;
  department?: string;
  disabled?: boolean;
  disabledReason?: string;
}

export const PERSONAS: Persona[] = [
  // Employees (3 active)
  {
    key: "northstar-asha",
    name: "Asha Rao",
    role: "Employee",
    tenant: "northstar",
    section: "employees",
    department: "Engineering",
  },
  {
    key: "northstar-kiran",
    name: "Kiran Desai",
    role: "Employee",
    tenant: "northstar",
    section: "employees",
    department: "Finance",
  },
  {
    key: "northstar-leena",
    name: "Leena Joseph",
    role: "Employee",
    tenant: "northstar",
    section: "employees",
    department: "Marketing",
  },
  // IT Support staff
  {
    key: "northstar-rahul",
    name: "Rahul Sharma",
    role: "IT Engineer",
    tenant: "northstar",
    section: "it_support",
    department: "IT Support",
  },
  {
    key: "northstar-priya",
    name: "Priya Menon",
    role: "IT Manager",
    tenant: "northstar",
    section: "it_support",
    department: "IT Operations",
  },
  {
    key: "northstar-vikram",
    name: "Vikram Rao",
    role: "Tenant Admin",
    tenant: "northstar",
    section: "it_support",
    department: "IT Security",
  },
  {
    key: "northstar-arjun-security",
    name: "Arjun Nair",
    role: "Security Analyst",
    tenant: "northstar",
    section: "it_support",
    department: "Security",
  },
];

export function personasBySection(section: PersonaSection): Persona[] {
  return PERSONAS.filter((p) => p.section === section && !p.disabled);
}

export function getPersonaByKey(key: string): Persona | undefined {
  return PERSONAS.find((p) => p.key === key);
}

export function getRoleNavItems(role: string): string[] {
  const base = ["/", "/support", "/tickets", "/devices"];

  if (["it_engineer", "it_manager", "tenant_admin", "security_analyst"].includes(role)) {
    base.push("/approvals");
  }

  if (role === "tenant_admin") {
    base.push("/admin");
  }

  if (role === "security_analyst") {
    base.push("/security");
  }

  return base;
}
