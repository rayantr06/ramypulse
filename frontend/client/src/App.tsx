import { Switch, Route, Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import Dashboard from "@/pages/Dashboard";
import Explorateur from "@/pages/Explorateur";
import Campagnes from "@/pages/Campagnes";
import Alertes from "@/pages/Alertes";
import Watchlists from "@/pages/Watchlists";
import Recommandations from "@/pages/Recommandations";
import AdminSources from "@/pages/AdminSources";

function AppRouter() {
  return (
    <Switch>
      <Route path="/" component={Dashboard} />
      <Route path="/explorateur" component={Explorateur} />
      <Route path="/campagnes" component={Campagnes} />
      <Route path="/watchlists" component={Watchlists} />
      <Route path="/alertes" component={Alertes} />
      <Route path="/recommandations" component={Recommandations} />
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
        <Router hook={useHashLocationWithSearchStripped}>
          <AppRouter />
        </Router>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
