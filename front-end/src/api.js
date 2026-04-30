const defaultBase = window.location.origin;

export function getApiBase() {
  return import.meta.env.VITE_API_BASE?.trim() || defaultBase;
}

export async function postJson(path, payload) {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }

  return response.json();
}

export async function postForm(path, formData) {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Upload failed");
  }

  return response.json();
}
