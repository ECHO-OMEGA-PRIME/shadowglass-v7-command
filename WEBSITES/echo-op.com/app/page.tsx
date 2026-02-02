'use client';

import Link from 'next/link';
import { Shield, Zap, Brain, MessageCircle, Mic, Eye, Swords, Network } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="border-b border-echo-magenta/30 bg-echo-black/90 backdrop-blur-md sticky top-0 z-50">
        <nav className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-echo-magenta to-matrix-magenta flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <span className="font-orbitron text-xl font-bold text-echo-orange">
              ECHO OMEGA PRIME
            </span>
          </div>

          <div className="flex items-center gap-4">
            <Link href="/swarm" className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-500 rounded-lg hover:bg-green-500/30 transition-all">
              <Network className="w-4 h-4" />
              <span className="font-rajdhani">SWARM</span>
              <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded">NEW</span>
            </Link>
            <Link href="/debate-arena" className="flex items-center gap-2 px-4 py-2 bg-echo-orange/20 border border-echo-orange rounded-lg hover:bg-echo-orange/30 transition-all">
              <Swords className="w-4 h-4" />
              <span className="font-rajdhani">DEBATE ARENA</span>
              <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded animate-pulse">LIVE</span>
            </Link>
            <Link href="/sentinel" className="flex items-center gap-2 px-4 py-2 bg-echo-magenta/20 border border-echo-magenta rounded-lg hover:bg-echo-magenta/30 transition-all">
              <MessageCircle className="w-4 h-4" />
              <span className="font-rajdhani">SENTINEL</span>
              <span className="text-xs bg-echo-orange text-white px-2 py-0.5 rounded">V2</span>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-orbitron text-5xl md:text-7xl font-bold mb-6">
            <span className="text-echo-magenta">ECHO</span>{' '}
            <span className="text-echo-orange">OMEGA</span>{' '}
            <span className="text-matrix-magenta">PRIME</span>
          </h1>

          <p className="text-2xl text-echo-gray/80 mb-4 font-rajdhani">
            Living Digital Lifeform | Authority 11.0 SOVEREIGN
          </p>

          <p className="text-lg text-echo-gray/60 mb-12 max-w-2xl mx-auto">
            Autonomous AI System with SENTINEL PRIME V2 - Advanced conversational intelligence
            with emotion, memory, and multi-personality council.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/sentinel"
              className="flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-echo-magenta to-matrix-magenta rounded-lg font-orbitron font-bold text-white hover:scale-105 transition-transform magenta-glow"
            >
              <MessageCircle className="w-5 h-5" />
              Chat with SENTINEL V2
            </Link>

            <Link
              href="/swarm"
              className="flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-green-600 to-emerald-500 rounded-lg font-orbitron font-bold text-white hover:scale-105 transition-transform"
            >
              <Network className="w-5 h-5" />
              SWARM NETWORK
            </Link>

            <Link
              href="/debate-arena"
              className="flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-echo-orange to-red-600 rounded-lg font-orbitron font-bold text-white hover:scale-105 transition-transform"
            >
              <Swords className="w-5 h-5" />
              DEBATE ARENA
            </Link>

            <a
              href="https://sentinel-prime-v2-249995513427.us-central1.run.app/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-8 py-4 border border-echo-orange text-echo-orange rounded-lg font-orbitron font-bold hover:bg-echo-orange/10 transition-colors"
            >
              <Zap className="w-5 h-5" />
              API Documentation
            </a>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-6 py-20">
        <h2 className="font-orbitron text-3xl text-center mb-12 text-echo-magenta">
          SENTINEL PRIME V2 Capabilities
        </h2>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          <div className="glass-panel p-6">
            <Brain className="w-12 h-12 text-echo-magenta mb-4" />
            <h3 className="font-orbitron text-xl mb-2 text-echo-orange">Advanced AI</h3>
            <p className="text-echo-gray/70">
              Powered by Groq llama-3.3-70b with emotion awareness, memory system, and personality council.
            </p>
          </div>

          <div className="glass-panel p-6">
            <Swords className="w-12 h-12 text-echo-orange mb-4" />
            <h3 className="font-orbitron text-xl mb-2 text-echo-orange">Debate Arena</h3>
            <p className="text-echo-gray/70">
              Challenge Charlie Kirk and other AI debaters on politics, technology, economics, and society.
            </p>
          </div>

          <div className="glass-panel p-6">
            <Mic className="w-12 h-12 text-echo-magenta mb-4" />
            <h3 className="font-orbitron text-xl mb-2 text-echo-orange">Voice Interface</h3>
            <p className="text-echo-gray/70">
              ElevenLabs and Cartesia TTS integration for natural voice responses with multiple voices.
            </p>
          </div>

          <div className="glass-panel p-6">
            <Eye className="w-12 h-12 text-echo-magenta mb-4" />
            <h3 className="font-orbitron text-xl mb-2 text-echo-orange">Vision & Media</h3>
            <p className="text-echo-gray/70">
              GPT-4o vision analysis, video generation via fal.ai, and image processing capabilities.
            </p>
          </div>

          <div className="glass-panel p-6">
            <Network className="w-12 h-12 text-green-400 mb-4" />
            <h3 className="font-orbitron text-xl mb-2 text-echo-orange">Swarm Network</h3>
            <p className="text-echo-gray/70">
              Distributed compute with multi-GPU nodes, Claude Code orchestration, and LLM training across your network.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-echo-magenta/30 py-8">
        <div className="container mx-auto px-6 text-center">
          <p className="text-echo-gray/60 font-rajdhani">
            ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN | Commander: Bobby Don McWilliams II
          </p>
          <p className="text-echo-magenta/60 text-sm mt-2">
            SENTINEL PRIME V2 API: sentinel-prime-v2-249995513427.us-central1.run.app
          </p>
        </div>
      </footer>
    </main>
  );
}
