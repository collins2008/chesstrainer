"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";

export default function Home() {
  const [platform, setPlatform] = useState("chess.com");
  const [username, setUsername] = useState("playerprincipal");
  const [targetRating, setTargetRating] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [timeBudget, setTimeBudget] = useState("");
  const [constraints, setConstraints] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiUrl, setApiUrl] = useState("http://127.0.0.1:8000");
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [engineStatus, setEngineStatus] = useState<any>(null);
  const reportRef = useRef<HTMLElement>(null);

  // Poll for engine status every 5 seconds
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (username) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${apiUrl}/status/${username}`);
          if (res.ok) {
            const data = await res.json();
            setEngineStatus(data);
          }
        } catch (e) {
          // ignore
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [username, apiUrl]);

  const handleSync = async () => {
    setSyncing(true);
    setError("");
    try {
      const res = await fetch(`${apiUrl}/sync/${platform}/${username}`, { 
        method: "POST",
        headers: { "Bypass-Tunnel-Reminder": "true" }
      });
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
    if (!username) {
      setError("Please fetch games first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${apiUrl}/report/${username}`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Bypass-Tunnel-Reminder": "true"
        },
        body: JSON.stringify({
          target_rating: targetRating,
          target_date: targetDate,
          time_budget: timeBudget,
          constraints: constraints,
          api_key: apiKey
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        setReport(data);
        setTimeout(() => {
          reportRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      } else {
        setError(data.message || "Failed to generate report.");
      }
    } catch (e) {
      setError("Failed to connect to backend.");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen p-8 pb-20 sm:p-20 font-[family-name:var(--font-geist-sans)] max-w-4xl mx-auto">
      <header className="flex flex-col gap-4 mb-10">
        <h1 className="text-4xl font-bold">AI Chess Coach</h1>
        <p className="text-gray-500">Your tournament-level assistant</p>
        <Link href="/chat" className="mt-2 inline-flex items-center text-blue-600 hover:text-blue-800 font-medium">
          Open Persistent Chat Coach &rarr;
        </Link>
      </header>

      <main className="flex flex-col gap-8">
        <section className="bg-gray-50 dark:bg-zinc-900 p-6 rounded-2xl border border-gray-200 dark:border-zinc-800">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Player Profile</h2>
            <div className="flex flex-col items-end gap-2 text-xs text-gray-500">
              <div className="flex items-center gap-2">
                <span>Backend URL:</span>
                <input 
                  type="text" 
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="border p-1 rounded bg-white dark:bg-black dark:text-white w-48 border-gray-300 dark:border-gray-700"
                  placeholder="http://localhost:8000"
                />
              </div>
              <div className="flex items-center gap-2">
                <span>Gemini API Key:</span>
                <input 
                  type="password" 
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="border p-1 rounded bg-white dark:bg-black dark:text-white w-48 border-gray-300 dark:border-gray-700"
                  placeholder="AI key (required)"
                />
              </div>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-4 items-center">
            <select 
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="border p-2 rounded bg-white dark:bg-black dark:text-white"
            >
              <option value="all">Both Platforms</option>
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
          </div>

          <div className="mt-8 bg-neutral-100 dark:bg-neutral-900 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800">
            <h3 className="text-xl font-bold mb-4">Set Your Coaching Goal</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium mb-1">Target Rating</label>
                <input 
                  type="text" 
                  value={targetRating}
                  onChange={(e) => setTargetRating(e.target.value)}
                  placeholder="e.g. 2000"
                  className="w-full border p-2 rounded bg-white dark:bg-black dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Timeline</label>
                <input 
                  type="text" 
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  placeholder="e.g. 6 months"
                  className="w-full border p-2 rounded bg-white dark:bg-black dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Weekly Time Budget</label>
                <input 
                  type="text" 
                  value={timeBudget}
                  onChange={(e) => setTimeBudget(e.target.value)}
                  placeholder="e.g. 5 hours"
                  className="w-full border p-2 rounded bg-white dark:bg-black dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Constraints</label>
                <input 
                  type="text" 
                  value={constraints}
                  onChange={(e) => setConstraints(e.target.value)}
                  placeholder="e.g. Weekends only"
                  className="w-full border p-2 rounded bg-white dark:bg-black dark:text-white"
                />
              </div>
            </div>

            <button 
              onClick={handleGenerate} 
              disabled={loading || !engineStatus || engineStatus.analyzed_games === 0}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white p-6 rounded-2xl font-bold shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed text-center"
            >
              <h2 className="text-xl mb-2">{loading ? "Generating Insight Report..." : "Generate Personalized Training Plan"}</h2>
              <p className="opacity-90 text-sm font-normal">Deep-dive diagnosis and custom study plan based on your games</p>
            </button>
          </div>

          {error && <p className="text-red-500 mt-4">{error}</p>}
          
          {engineStatus && engineStatus.total_games > 0 && (
            <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl border border-blue-100 dark:border-blue-900">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-blue-800 dark:text-blue-300">
                  Engine Analysis Progress
                </span>
                <span className="text-xs font-mono text-blue-600 dark:text-blue-400">
                  {engineStatus.analyzed_games} / {engineStatus.total_games} games
                </span>
              </div>
              <div className="w-full bg-blue-200 dark:bg-blue-950 rounded-full h-2.5">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-500" 
                  style={{ width: `${Math.max(5, (engineStatus.analyzed_games / engineStatus.total_games) * 100)}%` }}
                ></div>
              </div>
              {engineStatus.is_analyzing && (
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-2 animate-pulse">
                  Stockfish is currently crunching your games in the background...
                </p>
              )}
            </div>
          )}
        </section>

        {report && (
          <section ref={reportRef} className="animate-in fade-in slide-in-from-bottom-4 duration-500 mt-8 mb-16 border-t pt-8">
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
                    <p className="text-sm text-blue-600 dark:text-blue-400">Avg WP Loss</p>
                    <p className="text-2xl font-bold">{report.stats.engine_metrics.avg_wp_loss_per_move}</p>
                  </div>
                  <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-xl border border-amber-200 dark:border-amber-900 text-center">
                    <p className="text-sm text-amber-600 dark:text-amber-400">Overall CPL</p>
                    <p className="text-2xl font-bold">{report.stats.engine_metrics.avg_baseline_cpl}</p>
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
