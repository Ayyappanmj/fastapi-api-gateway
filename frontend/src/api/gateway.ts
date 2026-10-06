import { apiClient } from "./client";
import type { GatewayResponse, GatewayStatus } from "../types";

export async function sendGatewayRequest(
  targetService: string,
  method: string,
  path: string,
  body: Record<string, unknown> | null
): Promise<GatewayResponse> {
  const { data } = await apiClient.post<GatewayResponse>("/gateway/request", {
    target_service: targetService,
    method,
    path,
    body,
  });
  return data;
}

export async function getGatewayStatus(): Promise<GatewayStatus> {
  const { data } = await apiClient.get<GatewayStatus>("/gateway/status");
  return data;
}
