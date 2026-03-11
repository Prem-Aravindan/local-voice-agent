"use client";

import { useEffect, useRef, useState } from "react";
import { api, AudioRecord, Voice } from "../lib/api";

export default function GeneratePage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState("");
  const [text, setText] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [temperature, setTemperature] = useState(0.7);
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [audio, setAudio] = useState<AudioRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api
      .listVoices()
      .then((vs) => {
        const ready = vs.filter((v) => v.status === "ready");
        setVoices(ready);
        if (ready.length > 0) setVoiceId(ready[0].voice_id);
      })
      .catch(console.error);
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!voiceId || !text.trim()) return;
    setLoading(true);
    setError(null);
    setAudio(null);
    try {
      const result = await api.generateSpeech({
        voice_id: voiceId,
        text: text.trim(),
        language,
        speed,
        temperature,
      });
      setAudio(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">🔊 Generate Speech</h1>

      <form
        onSubmit={handleGenerate}
        className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm mb-6"
      >
        {/* Voice selector */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Voice</label>
          {voices.length === 0 ? (
            <p className="text-sm text-gray-500">
              No ready voices found.{" "}
              <a href="/voices" className="text-primary-600 underline">
                Train a voice first.
              </a>
            </p>
          ) : (
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Text input */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Text</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="Type the text you want to synthesise…"
            className="border rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            required
          />
        </div>

        {/* Parameters */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-xs font-medium mb-1">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="border rounded-lg px-2 py-1.5 text-sm w-full"
            >
              {["en", "es", "fr", "de", "it", "pt", "zh-cn", "ja"].map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">
              Speed: {speed.toFixed(1)}×
            </label>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">
              Temperature: {temperature.toFixed(1)}
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !voiceId}
          className="w-full bg-primary-600 text-white rounded-lg px-4 py-2.5 font-medium hover:bg-primary-700 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate Speech"}
        </button>
      </form>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {audio && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
          <h2 className="font-semibold mb-3">Generated Audio</h2>
          <audio
            ref={audioRef}
            controls
            autoPlay
            className="w-full mb-3"
            src={api.audioUrl(audio.audio_id)}
          />
          <div className="flex gap-3">
            <a
              href={api.audioUrl(audio.audio_id)}
              download={`${audio.audio_id}.wav`}
              className="text-sm text-primary-600 underline"
            >
              Download WAV
            </a>
            <span className="text-xs text-gray-400 self-center">
              ID: {audio.audio_id}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-2 italic">"{audio.text}"</p>
        </div>
      )}
    </div>
  );
}
