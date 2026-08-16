import Dashboard from "@/pages/Dashboard";
import { TenantInitializationGate } from "@/components/TenantInitializationGate";

export default function ProductHome() {
  return <TenantInitializationGate component={Dashboard} />;
}
