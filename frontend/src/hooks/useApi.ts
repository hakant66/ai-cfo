"use client";

import useSWR, { SWRConfiguration } from "swr";
import { apiDelete, apiDeleteWithBase, apiGet, apiGetWithBase, apiPatch, apiPatchWithBase, apiPost, apiPostForm, apiPostWithBase } from "@/lib/api";
import { getToken } from "@/lib/auth";

export function useAuthedSWR<T>(path: string, config?: SWRConfiguration<T, Error>) {
  const token = getToken();
  return useSWR<T, Error, [string, string | null] | null>(
    path ? [path, token] : null,
    ([url, tokenValue]) => apiGet<T>(url, tokenValue ?? undefined),
    config
  );
}

export function useAuthedSWRWithBase<T>(base: string, path: string, config?: SWRConfiguration<T, Error>) {
  const token = getToken();
  return useSWR<T, Error, [string, string, string | null] | null>(
    path ? [base, path, token] : null,
    ([baseUrl, url, tokenValue]) => apiGetWithBase<T>(baseUrl, url, tokenValue ?? undefined),
    config
  );
}

export async function postAuthed<T>(path: string, body: unknown) {
  const token = getToken();
  return apiPost<T>(path, body, token || undefined);
}

export async function postAuthedWithBase<T>(base: string, path: string, body: unknown) {
  const token = getToken();
  return apiPostWithBase<T>(base, path, body, token || undefined);
}

export async function patchAuthed<T>(path: string, body: unknown) {
  const token = getToken();
  return apiPatch<T>(path, body, token || undefined);
}

export async function patchAuthedWithBase<T>(base: string, path: string, body: unknown) {
  const token = getToken();
  return apiPatchWithBase<T>(base, path, body, token || undefined);
}

export async function postFormAuthed<T>(path: string, form: FormData) {
  const token = getToken();
  return apiPostForm<T>(path, form, token || undefined);
}

export async function deleteAuthed<T>(path: string) {
  const token = getToken();
  return apiDelete<T>(path, token || undefined);
}

export async function deleteAuthedWithBase<T>(base: string, path: string) {
  const token = getToken();
  return apiDeleteWithBase<T>(base, path, token || undefined);
}
