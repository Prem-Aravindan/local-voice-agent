export default function Home() {
  return (
    <div className="text-center py-16">
      <h1 className="text-4xl font-bold text-primary-700 mb-4">
        🎙️ Voice Clone Agent
      </h1>
      <p className="text-lg text-gray-600 mb-10 max-w-xl mx-auto">
        Record your voice, build a speaker profile, and synthesise natural-sounding
        speech — entirely on your local machine.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
        <a
          href="/voices"
          className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition text-left"
        >
          <div className="text-3xl mb-3">🗂️</div>
          <h2 className="font-semibold text-lg mb-1">Manage Voices</h2>
          <p className="text-sm text-gray-500">
            Create, view, and delete cloned voice profiles.
          </p>
        </a>
        <a
          href="/record"
          className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition text-left"
        >
          <div className="text-3xl mb-3">🎤</div>
          <h2 className="font-semibold text-lg mb-1">Record Voice</h2>
          <p className="text-sm text-gray-500">
            Follow the guided protocol to capture your voice samples.
          </p>
        </a>
        <a
          href="/generate"
          className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition text-left"
        >
          <div className="text-3xl mb-3">🔊</div>
          <h2 className="font-semibold text-lg mb-1">Generate Speech</h2>
          <p className="text-sm text-gray-500">
            Type any text and hear it spoken in your cloned voice.
          </p>
        </a>
      </div>
    </div>
  );
}
