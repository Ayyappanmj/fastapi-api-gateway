import { apiClient } from "./client";
import type { EndpointsResponse, OverviewStats, TrafficResponse } from "../types";

export async function getOverview(hours = 24): Promise<OverviewStats> {
  const { data } = await apiClient.get<OverviewStats>("/analytics/overview", { params: { hours } });
  return data;
}

export async function getTraffic(
  granularity: "hourly" | "daily" = "hourly",
  hours = 24,
  days = 7
): Promise<TrafficResponse> {
  const { data } = await apiClient.get<TrafficResponse>("/analytics/traffic", {
    params: { granularity, hours, days },
  });
  return data;
}

export async function getEndpointBreakdown(hours = 168, limit = 10): Promise<EndpointsResponse> {
  const { data } = await apiClient.get<EndpointsResponse>("/analytics/endpoints", {
    params: { hours, limit },
  });
  return data;
}
