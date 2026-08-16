import { AppShell } from "@/components/AppShell";
import AdminSourcesOps from "@/components/admin/AdminSourcesOps";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

export default function AdminSources() {
  return (
    <div data-testid="admin-shell-canvas">
      <AppShell
        avatarAlt={STITCH_AVATARS.admin.alt}
        avatarSrc={STITCH_AVATARS.admin.src}
        sidebarFooterSubtitle="Administration des flux"
      >
        <AdminSourcesOps />
      </AppShell>
    </div>
  );
}
