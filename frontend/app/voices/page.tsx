"use client";

import { useEffect, useState } from "react";
import { api, Voice } from "../lib/api";

export default function VoicesPage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadVoices = async () => {
    try {
      setVoices(await api.listVoices());
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    loadVoices();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.createVoice(name.trim(), description.trim() || undefined);
      setName("");
      setDescription("");
      await loadVoices();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async (voiceId: string) => {
    setError(null);
    try {
      await api.trainVoice(voiceId);
      alert("Training job enqueued. Refresh in a moment to check status.");
      await loadVoices();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (voiceId: string, voiceName: string) => {
    if (!confirm(`Delete voice "${voiceName}"?`)) return;
    try {
      await api.deleteVoice(voiceId);
      await loadVoices();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const statusBadge = (status: Voice["status"]) => {
    const colours: Record<Voice["status"], string> = {
      pending: "bg-yellow-100 text-yellow-800",
      ready: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
    };
    return (
      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colours[status]}`}>
        {status}
      </span>
    );
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">🗂️ Voice Profiles</h1>

      {/* Create voice form */}
      <form onSubmit={handleCreate} className="bg-white rounded-2xl border border-gray-200 p-6 mb-8 shadow-sm">
        <h2 className="font-semibold text-lg mb-4">Create New Voice</h2>
        <div className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Voice name (e.g. my_voice)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            required
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-primary-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "Creating…" : "Create Voice"}
          </button>
        </div>
      </form>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {/* Voice list */}
      {voices.length === 0 ? (
        <p className="text-gray-500 text-sm">No voices yet. Create one above.</p>
      ) : (
        <ul className="space-y-3">
          {voices.map((v) => (
            <li key={v.voice_id} className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex items-center justify-between">
              <div>
                <p className="font-medium">{v.name}</p>
                {v.description && <p className="text-sm text-gray-500">{v.description}</p>}
                <div className="mt-1">{statusBadge(v.status)}</div>
              </div>
              <div className="flex gap-2">
                {v.status !== "ready" && (
                  <button
                    onClick={() => handleTrain(v.voice_id)}
                    className="text-xs bg-primary-100 text-primary-700 px-3 py-1 rounded-lg hover:bg-primary-200"
                  >
                    Train
                  </button>
                )}
                <a
                  href={`/record?voice_id=${v.voice_id}`}
                  className="text-xs bg-gray-100 text-gray-700 px-3 py-1 rounded-lg hover:bg-gray-200"
                >
                  Record
                </a>
                <button
                  onClick={() => handleDelete(v.voice_id, v.name)}
                  className="text-xs bg-red-100 text-red-700 px-3 py-1 rounded-lg hover:bg-red-200"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
