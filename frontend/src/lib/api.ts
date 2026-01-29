function defaultBaseForPort(port: number) {
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:${port}`;
  }
  return `http://127.0.0.1:${port}`;
}

export function resolveApiBase() {
  return process.env.NEXT_PUBLIC_API_BASE || defaultBaseForPort(8000);
}

export function resolveWiseApiBase() {
  return process.env.NEXT_PUBLIC_WISE_API_BASE || defaultBaseForPort(8001);
}

function withBase(base: string, path: string) {
  return `${base}${path}`;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Request failed");
  }
  return res.json();
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(withBase(resolveApiBase(), path), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: "no-store"
  });
  return handleResponse<T>(res);
}

export async function apiPost<T>(path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(withBase(resolveApiBase(), path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  });
  return handleResponse<T>(res);
}

export async function apiPostForm<T>(path: string, form: FormData, token?: string): Promise<T> {
  const res = await fetch(withBase(resolveApiBase(), path), {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form
  });
  return handleResponse<T>(res);
}

export async function apiPatch<T>(path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(withBase(resolveApiBase(), path), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  });
  return handleResponse<T>(res);
}

export async function apiDelete<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(withBase(resolveApiBase(), path), {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined
  });
  return handleResponse<T>(res);
}

export async function apiGetWithBase<T>(base: string, path: string, token?: string): Promise<T> {
  const res = await fetch(withBase(base, path), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: "no-store"
  });
  return handleResponse<T>(res);
}

export async function apiPostWithBase<T>(base: string, path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(withBase(base, path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  });
  return handleResponse<T>(res);
}

export async function apiPatchWithBase<T>(base: string, path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(withBase(base, path), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  });
  return handleResponse<T>(res);
}

export async function apiDeleteWithBase<T>(base: string, path: string, token?: string): Promise<T> {
  const res = await fetch(withBase(base, path), {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined
  });
  return handleResponse<T>(res);
}
