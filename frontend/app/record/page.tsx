"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, Protocol, Voice } from "../lib/api";

const SECTION_LABELS: Record<string, string> = {
  warmup: "🔥 Warmup",
  storybook: "📖 Storybook Reading",
  numbers: "🔢 Numbers & Data",
  assistant: "🤖 Assistant Style",
  expressive: "🎭 Expressive Speech",
};

export default function RecordPage() {
  const searchParams = useSearchParams();
  const preselectedVoiceId = searchParams.get("voice_id") ?? "";

  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState(preselectedVoiceId);
  const [section, setSection] = useState("warmup");
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // For in-browser recording (WebRTC)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    api.listVoices().then(setVoices).catch(console.error);
    api.getProtocol().then(setProtocol).catch(console.error);
  }, []);

  const currentPrompts = protocol?.protocol[section] ?? [];

  const startRecording = async () => {
    if (!voiceId) {
      setError("Please select a voice first.");
      return;
    }
    setError(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.start();
      setIsRecording(true);
      setStatus("Recording…");
    } catch (e: any) {
      setError("Could not access microphone: " + e.message);
    }
  };

  const stopRecording = async () => {
    const mr = mediaRecorderRef.current;
    if (!mr) return;

    return new Promise<void>((resolve) => {
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], `sample_${Date.now()}.webm`, { type: "audio/webm" });
        setStatus("Uploading…");
        try {
          await api.uploadSample(voiceId, file, section);
          setStatus("✅ Sample saved!");
        } catch (e: any) {
          setError(e.message);
          setStatus(null);
        }
        mr.stream.getTracks().forEach((t) => t.stop());
        resolve();
      };
      mr.stop();
      setIsRecording(false);
    });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">🎤 Record Voice Samples</h1>

      {/* Voice selector */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6 shadow-sm">
        <label className="block text-sm font-medium mb-2">Select Voice Profile</label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">— choose a voice —</option>
          {voices.map((v) => (
            <option key={v.voice_id} value={v.voice_id}>
              {v.name}
            </option>
          ))}
        </select>
      </div>

      {/* Section selector */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6 shadow-sm">
        <label className="block text-sm font-medium mb-2">Recording Section</label>
        <div className="flex flex-wrap gap-2">
          {Object.entries(SECTION_LABELS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSection(key)}
              className={`text-sm px-3 py-1.5 rounded-lg border transition ${
                section === key
                  ? "bg-primary-600 text-white border-primary-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-primary-400"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Protocol prompts */}
      {currentPrompts.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 mb-6">
          <h2 className="font-semibold text-blue-800 mb-3">
            {SECTION_LABELS[section]} — Read aloud:
          </h2>
          <ul className="space-y-2">
            {currentPrompts.map((prompt, i) => (
              <li key={i} className="text-sm text-blue-900 bg-white rounded-lg p-3 border border-blue-100">
                {prompt}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recording controls */}
      <div className="flex gap-4 items-center">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={!voiceId}
            className="bg-red-600 text-white rounded-full px-6 py-3 font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
          >
            <span className="w-3 h-3 rounded-full bg-white inline-block" />
            Start Recording
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="bg-gray-800 text-white rounded-full px-6 py-3 font-medium hover:bg-gray-900 flex items-center gap-2 animate-pulse"
          >
            <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
            Stop Recording
          </button>
        )}
        {status && <span className="text-sm text-gray-600">{status}</span>}
      </div>

      {error && <p className="text-red-600 text-sm mt-4">{error}</p>}

      <p className="text-xs text-gray-400 mt-6">
        Tip: For best quality, record in a quiet environment and aim for at least 10 minutes
        of total audio across all sections.
      </p>
    </div>
  );
}
