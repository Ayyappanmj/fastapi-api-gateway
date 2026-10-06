import { AxiosError } from "axios";
import type { ApiErrorBody } from "../types";

export function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    if (body?.detail) return body.detail;
    if (body?.error) return body.error;
  }
  return fallback;
}
