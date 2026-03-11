import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Voice Clone Agent",
  description: "Local-first voice cloning and text-to-speech",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-5xl mx-auto px-4 py-3 flex gap-6 items-center">
            <span className="font-semibold text-primary-700 text-lg">🎙️ Voice Clone Agent</span>
            <a href="/" className="text-sm text-gray-600 hover:text-primary-600">Home</a>
            <a href="/voices" className="text-sm text-gray-600 hover:text-primary-600">Voices</a>
            <a href="/record" className="text-sm text-gray-600 hover:text-primary-600">Record</a>
            <a href="/generate" className="text-sm text-gray-600 hover:text-primary-600">Generate</a>
          </div>
        </nav>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
