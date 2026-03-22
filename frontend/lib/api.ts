const baseUrl = () =>
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "")

export async function sendMessage(
  message: string,
  sessionId: string,
  country: string
): Promise<{ answer: string }> {
  const res = await fetch(`${baseUrl()}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      country,
    }),
  })
  if (!res.ok) {
    let detail = ""
    try {
      const j = (await res.json()) as { detail?: string | { msg: string }[] }
      if (typeof j.detail === "string") detail = j.detail
    } catch {
      try {
        detail = await res.text()
      } catch {
        /* ignore */
      }
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export type AnalyticsPayload = {
  event_type: "country_select" | "form_download_click"
  country_code?: string
  country_label?: string
  link_url?: string
  link_text?: string
}

export function sendAnalyticsEvent(payload: AnalyticsPayload): void {
  const body = JSON.stringify(payload)
  void fetch(`${baseUrl()}/analytics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {})
}
