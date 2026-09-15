"use client";

import { useState } from "react";

export default function Home() {
  const [platform, setPlatform] = useState("chess.com");
  const [username, setUsername] = useState("playerprincipal");
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  const handleSync = async () => {
    setSyncing(true);
    setError("");
    try {
      const res = await fetch(`http://localhost:8000/sync/${platform}/${username}`, { method: "POST" });
      const data = await res.json();
      if (data.status === "error") {
        setError(data.message);
      } else {
        alert(data.message);
      }
    } catch (err: any) {
      setError(err.message || "Failed to sync");
    }
    setSyncing(false);
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setReport(null);
    try {
      const res = await fetch(`http://localhost:8000/report/${username}`);
      const data = await res.json();
      if (data.status === "error") {
        setError(data.message);
      } else {
        setReport(data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate report");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen p-8 pb-20 sm:p-20 font-[family-name:var(--font-geist-sans)] max-w-4xl mx-auto">
      <header className="flex flex-col gap-4 mb-10">
        <h1 className="text-4xl font-bold">AI Chess Coach</h1>
        <p className="text-gray-500">Your tournament-level assistant</p>
      </header>

      <main className="flex flex-col gap-8">
        <section className="bg-gray-50 dark:bg-zinc-900 p-6 rounded-2xl border border-gray-200 dark:border-zinc-800">
          <h2 className="text-2xl font-semibold mb-4">Player Profile</h2>
          <div className="flex flex-col sm:flex-row gap-4 items-center">
            <select 
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="border p-2 rounded bg-white dark:bg-black dark:text-white"
            >
              <option value="chess.com">Chess.com</option>
              <option value="lichess">Lichess</option>
            </select>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              className="border p-2 rounded w-full sm:w-auto flex-1 dark:bg-black dark:text-white"
              placeholder="Username"
            />
            <button 
              onClick={handleSync} 
              disabled={syncing}
              className="bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {syncing ? "Syncing..." : "Sync Games"}
            </button>
            <button 
              onClick={handleGenerate} 
              disabled={loading}
              className="bg-black text-white dark:bg-white dark:text-black px-4 py-2 rounded font-medium hover:bg-gray-800 dark:hover:bg-gray-200 disabled:opacity-50"
            >
              {loading ? "Generating..." : "Get Coaching Report"}
            </button>
          </div>
          {error && <p className="text-red-500 mt-4">{error}</p>}
        </section>

        {report && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-xl font-semibold mb-4">Core Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                <p className="text-sm text-gray-500">Games</p>
                <p className="text-2xl font-bold">{report.stats.total_games}</p>
              </div>
              <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                <p className="text-sm text-gray-500">Win Rate</p>
                <p className="text-2xl font-bold">{report.stats.win_rate}%</p>
              </div>
              <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                <p className="text-sm text-gray-500">Wins</p>
                <p className="text-2xl font-bold text-green-600">{report.stats.wins}</p>
              </div>
              <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                <p className="text-sm text-gray-500">Losses</p>
                <p className="text-2xl font-bold text-red-600">{report.stats.losses}</p>
              </div>
            </div>

            {report.stats.engine_metrics && (
              <>
                <h3 className="text-xl font-semibold mb-4 mt-8">Behavioral & Engine Analysis</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-xl border border-blue-200 dark:border-blue-900 text-center">
                    <p className="text-sm text-blue-600 dark:text-blue-400">Total Moves</p>
                    <p className="text-2xl font-bold">{report.stats.engine_metrics.total_moves_analyzed}</p>
                  </div>
                  <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-xl border border-amber-200 dark:border-amber-900 text-center">
                    <p className="text-sm text-amber-600 dark:text-amber-400">Overall CPL</p>
                    <p className="text-2xl font-bold">{report.stats.engine_metrics.average_centipawn_loss}</p>
                  </div>
                  <div className="bg-red-50 dark:bg-red-950 p-4 rounded-xl border border-red-200 dark:border-red-900 text-center">
                    <p className="text-sm text-red-600 dark:text-red-400">Total Blunders</p>
                    <p className="text-2xl font-bold text-red-600">{report.stats.engine_metrics.blunders}</p>
                  </div>
                  <div className="bg-purple-50 dark:bg-purple-950 p-4 rounded-xl border border-purple-200 dark:border-purple-900 text-center">
                    <p className="text-sm text-purple-600 dark:text-purple-400">Complacency Blunders</p>
                    <p className="text-2xl font-bold text-purple-600">{report.stats.engine_metrics.complacency_blunders}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                    <p className="text-sm text-gray-500">Opening CPL</p>
                    <p className="text-xl font-bold">{report.stats.engine_metrics.cpl_opening}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                    <p className="text-sm text-gray-500">Middlegame CPL</p>
                    <p className="text-xl font-bold">{report.stats.engine_metrics.cpl_middlegame}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                    <p className="text-sm text-gray-500">Endgame CPL</p>
                    <p className="text-xl font-bold">{report.stats.engine_metrics.cpl_endgame}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-zinc-900 p-4 rounded-xl border border-gray-200 dark:border-zinc-800 text-center">
                    <p className="text-sm text-gray-500">Time-Pressure CPL</p>
                    <p className="text-xl font-bold">{report.stats.engine_metrics.cpl_under_60s}</p>
                  </div>
                </div>
              </>
            )}

            <h3 className="text-xl font-semibold mb-4 mt-8">AI Coach Assessment</h3>
            <div className="prose dark:prose-invert max-w-none">
              <div className="bg-white dark:bg-black p-8 rounded-2xl border border-gray-200 dark:border-zinc-800 shadow-sm whitespace-pre-wrap leading-relaxed">
                {report.report}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
