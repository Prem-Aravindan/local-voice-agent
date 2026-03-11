/**
 * API client utilities for the Voice Clone Agent backend.
 */

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface Voice {
  voice_id: string;
  name: string;
  description: string | null;
  status: "pending" | "ready" | "failed";
  embedding_path: string | null;
  samples_path: string | null;
  created_at: string;
}

export interface TrainingJob {
  job_id: string;
  voice_id: string;
  status: string;
}

export interface AudioRecord {
  audio_id: string;
  voice_id: string;
  text: string;
  file_path: string;
  speed: number;
  temperature: number;
  created_at: string;
}

export interface Protocol {
  protocol: Record<string, string[]>;
}

export interface TTSRequest {
  voice_id: string;
  text: string;
  language?: string;
  speed?: number;
  temperature?: number;
}

export const api = {
  listVoices: () => request<Voice[]>("/voices"),
  getVoice: (voiceId: string) => request<Voice>(`/voice/${voiceId}`),
  createVoice: (name: string, description?: string) =>
    request<Voice>("/voice/create", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  deleteVoice: (voiceId: string) =>
    fetch(`${BASE}/voice/${voiceId}`, { method: "DELETE" }),
  trainVoice: (voiceId: string) =>
    request<TrainingJob>(`/voice/${voiceId}/train`, { method: "POST" }),
  getProtocol: () => request<Protocol>("/voice/protocol"),
  uploadSample: (voiceId: string, file: File, section = "warmup") => {
    const form = new FormData();
    form.append("voice_id", voiceId);
    form.append("section", section);
    form.append("file", file);
    return fetch(`${BASE}/voice/sample`, { method: "POST", body: form }).then(
      (r) => r.json()
    );
  },
  generateSpeech: (req: TTSRequest) =>
    request<AudioRecord>("/tts", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  audioUrl: (audioId: string) => `${BASE}/audio/${audioId}`,
};
