import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background">
      <Card className="w-full max-w-md mx-4 border-outline-variant/20 bg-surface-container text-on-surface">
        <CardContent className="pt-6">
          <div className="flex mb-4 gap-2">
            <AlertCircle className="h-8 w-8 text-error" />
            <h1 className="text-2xl font-bold text-on-surface">404 • Page introuvable</h1>
          </div>

          <p className="mt-4 text-sm text-on-surface-variant">
            Cette page n'existe pas ou a été déplacée.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
