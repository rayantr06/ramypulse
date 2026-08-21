import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/hooks/use-toast";
import {
  listeningPointsRepository,
  type ListeningPointCreateInput,
  type ListeningPointStatus,
  type ListeningPointSubmissionInput,
} from "@/lib/listeningPoints";
import { useTenantId } from "@/lib/tenantContext";

const listeningPointsKey = (organizationId: string) => [
  "/api/v3/listening-points",
  { clientId: organizationId },
] as const;

const listeningPointSubmissionsKey = (organizationId: string, pointId: string) => [
  "/api/v3/listening-point-submissions",
  { clientId: organizationId, pointId },
] as const;

const listeningPointSubmissionsPrefix = (organizationId: string) => [
  "/api/v3/listening-point-submissions",
  { clientId: organizationId },
] as const;

function useListeningPointsOrganizationId(): string {
  return useTenantId() ?? "demo-expo-2026";
}

function useMutationErrorToast() {
  const { toast } = useToast();
  return (error: Error) => toast({
    variant: "destructive",
    title: "Opération impossible",
    description: error.message,
  });
}

function refreshListeningPointQueries(queryClient: ReturnType<typeof useQueryClient>, organizationId: string) {
  queryClient.setQueryData(listeningPointsKey(organizationId), listeningPointsRepository.list(organizationId));
  return queryClient.invalidateQueries({ queryKey: listeningPointSubmissionsPrefix(organizationId) });
}

export function useListeningPoints() {
  const organizationId = useListeningPointsOrganizationId();

  return useQuery({
    queryKey: listeningPointsKey(organizationId),
    queryFn: () => Promise.resolve(listeningPointsRepository.list(organizationId)),
  });
}

export function useListeningPointSubmissions(pointId: string) {
  const organizationId = useListeningPointsOrganizationId();

  return useQuery({
    queryKey: listeningPointSubmissionsKey(organizationId, pointId),
    queryFn: () => {
      const point = listeningPointsRepository.list(organizationId).find((item) => item.id === pointId);
      return Promise.resolve(point ? listeningPointsRepository.listSubmissions(pointId) : []);
    },
  });
}

export function useCreateListeningPoint() {
  const organizationId = useListeningPointsOrganizationId();
  const queryClient = useQueryClient();
  const onError = useMutationErrorToast();

  return useMutation({
    mutationFn: (input: Omit<ListeningPointCreateInput, "organizationId">) => Promise.resolve(
      listeningPointsRepository.create({ ...input, organizationId }),
    ),
    onSuccess: () => refreshListeningPointQueries(queryClient, organizationId),
    onError,
  });
}

export function useSubmitListeningPointFeedback() {
  const organizationId = useListeningPointsOrganizationId();
  const queryClient = useQueryClient();
  const onError = useMutationErrorToast();

  return useMutation({
    mutationFn: (input: Omit<ListeningPointSubmissionInput, "organizationId">) => Promise.resolve(
      listeningPointsRepository.submit({ ...input, organizationId }),
    ),
    onSuccess: (submission) => {
      queryClient.setQueryData(
        listeningPointSubmissionsKey(organizationId, submission.listeningPointId),
        listeningPointsRepository.listSubmissions(submission.listeningPointId),
      );
      return queryClient.invalidateQueries({ queryKey: listeningPointsKey(organizationId) });
    },
    onError,
  });
}

export function useSetListeningPointStatus() {
  const organizationId = useListeningPointsOrganizationId();
  const queryClient = useQueryClient();
  const onError = useMutationErrorToast();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ListeningPointStatus }) => {
      const point = listeningPointsRepository.list(organizationId).find((item) => item.id === id);
      if (!point) return Promise.reject(new Error("Point d'écoute introuvable pour cette organisation."));
      return Promise.resolve(listeningPointsRepository.setStatus(id, status));
    },
    onSuccess: () => refreshListeningPointQueries(queryClient, organizationId),
    onError,
  });
}
