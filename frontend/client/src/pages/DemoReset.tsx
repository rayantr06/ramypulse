import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { useLocation } from "wouter";

import { BrandMark } from "@/components/BrandMark";
import { resetLeticiaDemoState } from "@/lib/leticiaDemoState";

export default function DemoReset() {
  const queryClient = useQueryClient();
  const [, setLocation] = useLocation();
  const didReset = useRef(false);

  useEffect(() => {
    if (didReset.current) return;
    didReset.current = true;
    resetLeticiaDemoState(window.localStorage);
    queryClient.clear();
    const timeout = window.setTimeout(() => setLocation("/"), 800);
    return () => window.clearTimeout(timeout);
  }, [queryClient, setLocation]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface-container-lowest p-5 text-on-surface">
      <section className="w-full max-w-md rounded-[2rem] border border-outline-variant bg-surface p-7 text-center shadow-ambient">
        <BrandMark />
        <span className="mx-auto mt-8 flex h-16 w-16 items-center justify-center rounded-full bg-action-container text-action">
          <CheckCircle2 className="h-8 w-8" aria-hidden="true" />
        </span>
        <h1 className="mt-5 font-headline text-3xl font-semibold">Démonstration réinitialisée</h1>
        <p className="mt-3 text-sm leading-6 text-on-surface-variant">Les données locales Leticia ont été effacées. Retour à l’accueil…</p>
      </section>
    </main>
  );
}
