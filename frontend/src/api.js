const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8010";


export async function createMeeting(meetingData) {
  return request("/meetings", {
    method: "POST",
    body: JSON.stringify(meetingData),
  });
}


export async function getMeetings() {
  return request("/meetings");
}


export async function getMeeting(meetingId) {
  return request(`/meetings/${meetingId}`);
}


export async function getMeetingActionItems(meetingId, owner = "") {
  const query = owner ? `?owner=${encodeURIComponent(owner)}` : "";
  return request(`/meetings/${meetingId}/action-items${query}`);
}


export async function updateActionItem(actionItemId, updates) {
  return request(`/action-items/${actionItemId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}


export async function exportMeeting(meetingId) {
  return request(`/meetings/${meetingId}/export`);
}


async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "API request failed");
  }

  return data;
}
