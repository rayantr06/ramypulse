import Dashboard from "@/pages/Dashboard";
import WatchOnboarding from "@/pages/WatchOnboarding";
import { useTenantId } from "@/lib/tenantContext";

export default function ProductHome() {
  const tenantId = useTenantId();

  return tenantId ? <Dashboard /> : <WatchOnboarding />;
}
