import { useEffect, useRef, type ComponentType } from "react";
import { Switch, Route, Router, useLocation } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useTenantId } from "@/lib/tenantContext";
import NotFound from "@/pages/not-found";
import Explorateur from "@/pages/Explorateur";
import Campagnes from "@/pages/Campagnes";
import Alertes from "@/pages/Alertes";
import Watchlists from "@/pages/Watchlists";
import Recommandations from "@/pages/Recommandations";
import AdminSources from "@/pages/AdminSources";
import ProductHome from "@/pages/ProductHome";
import WatchOnboarding from "@/pages/WatchOnboarding";

function TenantCacheReset() {
  const tenantId = useTenantId();
  const previousTenantId = useRef<string | null>(tenantId);

  useEffect(() => {
    if (previousTenantId.current !== tenantId) {
      queryClient.clear();
      previousTenantId.current = tenantId;
    }
  }, [tenantId]);

  return null;
}

function TenantProtectedRoute({ component: Component }: { component: ComponentType }) {
  const tenantId = useTenantId();
  const [location, setLocation] = useLocation();

  useEffect(() => {
    if (!tenantId && location !== "/nouveau-client") {
      setLocation("/nouveau-client");
    }
  }, [location, setLocation, tenantId]);

  if (!tenantId) {
    return <WatchOnboarding />;
  }

  return <Component />;
}

function AppRouter() {
  return (
    <Switch>
      <Route path="/" component={ProductHome} />
      <Route path="/nouveau-client" component={WatchOnboarding} />
      <Route path="/explorateur" component={() => <TenantProtectedRoute component={Explorateur} />} />
      <Route path="/campagnes" component={() => <TenantProtectedRoute component={Campagnes} />} />
      <Route path="/watchlists" component={() => <TenantProtectedRoute component={Watchlists} />} />
      <Route path="/alertes" component={() => <TenantProtectedRoute component={Alertes} />} />
      <Route
        path="/recommandations"
        component={() => <TenantProtectedRoute component={Recommandations} />}
      />
      <Route path="/admin-sources" component={AdminSources} />
      <Route component={NotFound} />
    </Switch>
  );
}

function useHashLocationWithSearchStripped(): ReturnType<typeof useHashLocation> {
  const [location, navigate] = useHashLocation();
  const normalizedLocation = location.split("?")[0] || "/";
  return [normalizedLocation, navigate];
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <TenantCacheReset />
        <Router hook={useHashLocationWithSearchStripped}>
          <AppRouter />
        </Router>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
