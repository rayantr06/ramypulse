import { lazy, Suspense, useEffect, type ComponentType } from "react";
import { Switch, Route, Router, useLocation } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { getTenantQueryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useTenantId } from "@/lib/tenantContext";
import { useTenantReadiness } from "@/lib/tenantReadiness";
import { shouldGateProductRoute } from "@/lib/routeAccess";
import { TenantReadinessScreen } from "@/components/TenantReadinessScreen";
const NotFound = lazy(() => import("@/pages/not-found"));
const Explorateur = lazy(() => import("@/pages/Explorateur"));
const Campagnes = lazy(() => import("@/pages/Campagnes"));
const Watchlists = lazy(() => import("@/pages/Watchlists"));
const AdminSources = lazy(() => import("@/pages/AdminSources"));
const ProductHome = lazy(() => import("@/pages/ProductHome"));
const WatchOnboarding = lazy(() => import("@/pages/WatchOnboarding"));
const Signals = lazy(() => import("@/pages/Signals"));
const Actions = lazy(() => import("@/pages/Actions"));
const Reports = lazy(() => import("@/pages/Reports"));
const ListeningPoints = lazy(() => import("@/pages/ListeningPoints"));
const ListeningPointComposer = lazy(() => import("@/components/listening/ListeningPointComposer"));
const PublicFeedback = lazy(() => import("@/pages/PublicFeedback"));
const DemoReset = lazy(() => import("@/pages/DemoReset"));

function LegacyRedirect({ to }: { to: string }) {
  const [, setLocation] = useLocation();
  useEffect(() => setLocation(to), [setLocation, to]);
  return <TenantReadinessScreen />;
}

function TenantProtectedRoute({ component: Component }: { component: ComponentType }) {
  const readiness = useTenantReadiness();
  const [location, setLocation] = useLocation();
  const path = location.split("?")[0] || "/";

  useEffect(() => {
    if (shouldGateProductRoute(path, readiness.state) && path !== "/nouveau-client") {
      setLocation("/nouveau-client");
    }
  }, [path, readiness.state, setLocation]);

  if (readiness.state === "checking") {
    return <TenantReadinessScreen />;
  }

  if (shouldGateProductRoute(path, readiness.state)) {
    return <WatchOnboarding />;
  }

  return <Component />;
}

function AppRouter() {
  return (
    <Suspense fallback={<TenantReadinessScreen />}>
      <Switch>
      <Route path="/" component={ProductHome} />
      <Route path="/nouveau-client" component={WatchOnboarding} />
      <Route path="/explorateur" component={() => <TenantProtectedRoute component={Explorateur} />} />
      <Route path="/campagnes" component={() => <TenantProtectedRoute component={Campagnes} />} />
      <Route path="/watchlists/new" component={() => <TenantProtectedRoute component={Watchlists} />} />
      <Route path="/watchlists" component={() => <TenantProtectedRoute component={Watchlists} />} />
      <Route path="/signals" component={() => <TenantProtectedRoute component={Signals} />} />
      <Route path="/actions" component={() => <TenantProtectedRoute component={Actions} />} />
      <Route path="/reports" component={() => <TenantProtectedRoute component={Reports} />} />
      <Route path="/listening-points/new" component={() => <TenantProtectedRoute component={ListeningPointComposer} />} />
      <Route path="/listening-points" component={() => <TenantProtectedRoute component={ListeningPoints} />} />
      {/* Public collection and reset must stay usable without tenant onboarding. */}
      <Route path="/feedback/:token" component={PublicFeedback} />
      <Route path="/demo/reset" component={DemoReset} />
      <Route path="/sources" component={AdminSources} />
      <Route path="/alertes" component={() => <LegacyRedirect to="/signals" />} />
      <Route path="/recommandations" component={() => <LegacyRedirect to="/actions" />} />
      {/* /admin-sources is intentionally outside the tenant gate: it is the operator console. */}
      <Route path="/admin-sources" component={AdminSources} />
      <Route component={NotFound} />
      </Switch>
    </Suspense>
  );
}

function useHashLocationWithSearchStripped(): ReturnType<typeof useHashLocation> {
  const [location, navigate] = useHashLocation();
  const normalizedLocation = location.split("?")[0] || "/";
  return [normalizedLocation, navigate];
}

function App() {
  const tenantId = useTenantId();
  const queryClient = getTenantQueryClient(tenantId);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Router hook={useHashLocationWithSearchStripped}>
          <AppRouter />
        </Router>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
