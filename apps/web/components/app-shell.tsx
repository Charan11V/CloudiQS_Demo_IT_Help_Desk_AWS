"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { auth, notifications } from "@/lib/api-client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Home,
  LifeBuoy,
  Ticket,
  MonitorSmartphone,
  CheckSquare,
  Settings,
  Shield,
  Bell,
  LogOut,
  PanelLeftClose,
  PanelLeft,
  Menu,
  X,
} from "lucide-react";
import { HelioLogo, DemoIndicator, HelioButton, Skeleton } from "@/components/helio";
import { cn } from "@/lib/utils";

type Role =
  | "employee"
  | "contractor"
  | "it_engineer"
  | "it_manager"
  | "tenant_admin"
  | "security_analyst"
  | "hr_partner"
  | string;

function allowedHrefs(role: Role | undefined | null): Set<string> {
  const base = ["/", "/support", "/tickets", "/devices"];
  const ops = ["/approvals"];
  const admin = ["/admin"];
  const sec = ["/security"];
  const set = new Set(base);
  if (!role || role === "employee" || role === "contractor") return set;
  if (role === "it_engineer") {
    ops.forEach((h) => set.add(h));
    return set;
  }
  if (role === "it_manager") {
    ops.forEach((h) => set.add(h));
    return set;
  }
  if (role === "tenant_admin") {
    [...ops, ...admin].forEach((h) => set.add(h));
    return set;
  }
  if (role === "security_analyst") {
    ["/approvals", ...sec].forEach((h) => set.add(h));
    return set;
  }
  [...ops, ...admin, ...sec].forEach((h) => set.add(h));
  return set;
}

const NAV_SECTIONS = [
  {
    section: "Workspace",
    items: [
      { href: "/", icon: Home, label: "Home" },
      { href: "/support", icon: LifeBuoy, label: "Get help" },
      { href: "/tickets", icon: Ticket, label: "My tickets" },
      { href: "/devices", icon: MonitorSmartphone, label: "My devices" },
    ],
  },
  {
    section: "Operations",
    items: [
      { href: "/approvals", icon: CheckSquare, label: "Approvals" },
    ],
  },
  {
    section: "Management",
    items: [
      { href: "/admin", icon: Settings, label: "Admin" },
      { href: "/security", icon: Shield, label: "Security" },
    ],
  },
];

function NavBody({
  collapsed,
  pathname,
  navItems,
  onNavigate,
}: {
  collapsed: boolean;
  pathname: string;
  navItems: typeof NAV_SECTIONS;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex-1 overflow-y-auto px-3 py-4">
      {navItems.map((section) => (
        <div key={section.section} className="mb-5">
          {!collapsed && (
            <div className="px-3 mb-2 text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--ink-tertiary)]">
              {section.section}
            </div>
          )}
          <div className="space-y-0.5">
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  title={collapsed ? item.label : undefined}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                    isActive
                      ? "bg-[var(--signal-soft)] text-[var(--signal)] font-medium"
                      : "text-[var(--ink-secondary)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--ink)]"
                  )}
                >
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-[var(--signal)]" />
                  )}
                  <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

  const { data: session, isLoading, isError } = useQuery({
    queryKey: ["session"],
    queryFn: auth.getSession,
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const { data: notifList } = useQuery({
    queryKey: ["notifications"],
    queryFn: notifications.list,
    enabled: !!session,
    refetchInterval: 60_000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notifications.markRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Could not mark read");
    },
  });

  const unreadCount = (notifList || []).filter((n: { read?: boolean }) => !n.read).length;

  useEffect(() => {
    // Full navigation avoids soft-nav races with demo-gate middleware on hard refresh
    if (!isLoading && (isError || !session)) {
      window.location.replace("/login");
    }
  }, [session, isLoading, isError]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileOpen]);

  const handleLogout = async () => {
    await auth.logout();
    queryClient.clear();
    router.push("/login");
  };

  const role = (session as { role?: string } | undefined)?.role;
  const allowed = useMemo(() => allowedHrefs(role), [role]);
  const navItems = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((i) => allowed.has(i.href)),
  })).filter((section) => section.items.length > 0);

  if (isLoading || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas">
        <div className="space-y-3 w-48">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-2/3 mx-auto" />
        </div>
      </div>
    );
  }

  const initials = (session.name || session.user_id || "??")
    .split(/\s|-/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s: string) => s[0]?.toUpperCase())
    .join("");

  const tenantLabel =
    session.tenant_id === "northstar"
      ? "Northstar Enterprise workspace"
      : `${session.tenant_id} workspace`;

  const crumb =
    pathname === "/"
      ? "Home"
      : pathname
          .split("/")
          .filter(Boolean)
          .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
          .join(" / ");

  const rail = (collapsed: boolean, onNavigate?: () => void) => (
    <aside
      className={cn(
        "bg-sidebar-rail text-[var(--sidebar-ink)] flex flex-col h-full border-r border-[var(--stroke)]",
        collapsed ? "w-[72px]" : "w-[256px]"
      )}
    >
      <div
        className={cn(
          "h-[72px] flex items-center border-b border-[var(--stroke)]",
          collapsed ? "px-4 justify-center" : "px-5 gap-3"
        )}
      >
        <HelioLogo size={collapsed ? 24 : 28} />
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-[15px] font-semibold tracking-[-0.03em] leading-tight text-[var(--ink)]">
              CloudiQS Demo agent
            </div>
            <div className="text-[11px] text-[var(--ink-tertiary)] truncate">{tenantLabel}</div>
          </div>
        )}
      </div>

      <NavBody
        collapsed={collapsed}
        pathname={pathname}
        navItems={navItems}
        onNavigate={onNavigate}
      />

      <div className="p-3 border-t border-[var(--stroke)] space-y-3">
        {!collapsed && (
          <div className="px-2">
            <DemoIndicator />
          </div>
        )}
        <div className={cn("flex items-center gap-2.5 px-2 py-1.5", collapsed && "justify-center")}>
          <div className="h-9 w-9 rounded-full bg-brand-gradient text-white flex items-center justify-center text-xs font-medium shadow-soft">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate text-[var(--ink)]">{session.name || session.user_id}</div>
              <div className="text-[11px] text-[var(--ink-tertiary)] truncate">
                {session.role} · {session.tenant_id}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );

  const fillViewport = pathname === "/support";

  return (
    <div className="h-dvh max-h-dvh overflow-hidden flex bg-canvas">
      <div className="hidden lg:flex shrink-0 h-full">
        {rail(sidebarCollapsed)}
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-[min(100vw-48px,300px)] max-w-[300px] shadow-raised safe-area-nav">
            {rail(false, () => setMobileOpen(false))}
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 min-h-0 w-full overflow-hidden">
        <header className="z-40 h-[56px] sm:h-[68px] shrink-0 border-b border-stroke bg-[var(--surface)]/95 backdrop-blur-sm flex items-center justify-between px-3 sm:px-8 pt-[env(safe-area-inset-top)]">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <HelioButton
              variant="quiet"
              size="icon"
              className="lg:hidden h-11 w-11"
              aria-label="Open navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </HelioButton>
            <HelioButton
              variant="quiet"
              size="icon"
              className="hidden lg:inline-flex"
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setSidebarCollapsed((c) => !c)}
            >
              {sidebarCollapsed ? (
                <PanelLeft className="h-5 w-5" />
              ) : (
                <PanelLeftClose className="h-5 w-5" />
              )}
            </HelioButton>
            <div className="min-w-0">
              <h1 className="text-base sm:text-lg font-semibold tracking-[-0.02em] text-[var(--ink)] truncate">
                {crumb}
              </h1>
              <p className="hidden sm:block text-[11px] text-[var(--ink-tertiary)] truncate">
                {tenantLabel}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            {session?.role ? (
              <span className="hidden md:inline-flex items-center rounded-lg bg-[var(--signal-soft)] px-2.5 py-1 text-[11px] font-medium text-[var(--signal)] capitalize">
                {String(session.role).replace(/_/g, " ")}
              </span>
            ) : null}
            <div className="relative">
              <HelioButton
                variant="quiet"
                size="icon"
                aria-label="Notifications"
                onClick={() => setNotifOpen((o) => !o)}
              >
                <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
                {unreadCount > 0 && (
                  <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-[var(--magenta)] text-[10px] text-white flex items-center justify-center">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </HelioButton>
              {notifOpen && (
                <div className="absolute right-0 mt-2 w-[min(calc(100vw-1.5rem),20rem)] max-h-[min(24rem,70vh)] overflow-y-auto rounded-2xl border border-stroke bg-[var(--surface)] shadow-raised z-50">
                  <div className="px-4 py-3 border-b border-stroke text-sm font-medium flex items-center justify-between">
                    Notifications
                    <button type="button" aria-label="Close" onClick={() => setNotifOpen(false)}>
                      <X className="h-4 w-4 text-[var(--ink-tertiary)]" />
                    </button>
                  </div>
                  {(notifList || []).length === 0 ? (
                    <div className="p-5 text-sm text-[var(--ink-secondary)]">No notifications</div>
                  ) : (
                    (notifList || []).slice(0, 15).map((n: {
                      notification_id: string;
                      read?: boolean;
                      link?: string;
                      title?: string;
                      body?: string;
                    }) => (
                      <button
                        key={n.notification_id}
                        type="button"
                        className={cn(
                          "w-full text-left px-4 py-3 border-b border-stroke last:border-0 hover:bg-[var(--surface-hover)]",
                          n.read && "opacity-70"
                        )}
                        onClick={() => {
                          if (!n.read) markReadMutation.mutate(n.notification_id);
                          if (n.link) {
                            setNotifOpen(false);
                            router.push(n.link);
                          }
                        }}
                      >
                        <div className="text-sm font-medium text-[var(--ink)]">{n.title}</div>
                        {n.body && (
                          <div className="text-xs text-[var(--ink-secondary)] line-clamp-2 mt-0.5">
                            {n.body}
                          </div>
                        )}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            <HelioButton variant="quiet" size="icon" onClick={handleLogout} aria-label="Sign out">
              <LogOut className="h-[18px] w-[18px]" strokeWidth={1.75} />
            </HelioButton>
          </div>
        </header>

        <main
          className={cn(
            "flex-1 min-h-0 overscroll-contain",
            fillViewport ? "overflow-hidden" : "overflow-auto"
          )}
        >
          {fillViewport ? (
            <div className="h-full min-h-0 w-full px-3 sm:px-6 py-3 sm:py-4 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
              {children}
            </div>
          ) : (
            <div className="mx-auto w-full max-w-[1320px] px-3 sm:px-8 py-5 sm:py-10 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
              {children}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
