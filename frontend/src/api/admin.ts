import { apiClient } from "./client";
import type { BlockedRequestEntry, PaginatedResponse, RequestLogEntry, User } from "../types";

export async function listUsers(page = 1, pageSize = 20): Promise<PaginatedResponse<User>> {
  const { data } = await apiClient.get<PaginatedResponse<User>>("/admin/users", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function listLogs(
  page = 1,
  pageSize = 20,
  endpoint?: string
): Promise<PaginatedResponse<RequestLogEntry>> {
  const { data } = await apiClient.get<PaginatedResponse<RequestLogEntry>>("/admin/logs", {
    params: { page, page_size: pageSize, endpoint: endpoint || undefined },
  });
  return data;
}

export async function listBlocked(
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<BlockedRequestEntry>> {
  const { data } = await apiClient.get<PaginatedResponse<BlockedRequestEntry>>("/admin/blocked", {
    params: { page, page_size: pageSize },
  });
  return data;
}
