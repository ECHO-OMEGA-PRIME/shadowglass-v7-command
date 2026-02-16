'use client';

import Image from 'next/image';
import { useEffect, useState, useRef } from 'react';

function useAutoTheme() {
  const [isDark, setIsDark] = useState(false);
  useEffect(() => {
    const check = () => { const h = new Date().getHours(); setIsDark(h < 6 || h >= 18); };
    check();
    const i = setInterval(check, 60_000);
    return () => clearInterval(i);
  }, []);
  useEffect(() => { document.documentElement.classList.toggle('dark', isDark); }, [isDark]);
  return { isDark, toggle: () => setIsDark(d => !d) };
}

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

const CAPABILITIES = [
  {
    title: 'Intelligence Engines',
    description: 'Purpose-built AI reasoning systems with deep domain expertise. Each engine understands its vertical the way a senior analyst would — not a generic chatbot.',
    stat: '1,100+',
    statLabel: 'Engines Live',
    icon: '⬡',
  },
  {
    title: 'Autonomous Data Pipelines',
    description: 'Systems that find, extract, normalize, and deliver structured data from thousands of sources — running 24/7 without human intervention.',
    stat: '59',
    statLabel: 'Verticals',
    icon: '◈',
  },
  {
    title: 'Edge Infrastructure',
    description: 'Globally distributed architecture with sub-50ms response times. No cold starts, no downtime, no single points of failure.',
    stat: '<50ms',
    statLabel: 'Global Latency',
    icon: '◇',
  },
  {
    title: 'Knowledge Systems',
    description: 'Proprietary knowledge graphs with tens of thousands of embedded reasoning blocks. Hybrid retrieval that combines precision search with semantic understanding.',
    stat: '30K+',
    statLabel: 'Knowledge Blocks',
    icon: '△',
  },
  {
    title: 'Multi-Model Orchestration',
    description: 'Intelligent routing across dozens of AI models. Automatic failover, cost optimization, and model selection tuned per query type.',
    stat: '30+',
    statLabel: 'AI Models',
    icon: '⬢',
  },
  {
    title: 'Enterprise Security',
    description: 'Military-grade encryption, automated threat monitoring, zero-trust access control, and complete audit trails for every operation.',
    stat: '256-bit',
    statLabel: 'AES Encryption',
    icon: '⬟',
  },
];

const INDUSTRIES = [
  'Oil & Gas', 'Legal', 'Tax & Accounting', 'Land & Title',
  'Cybersecurity', 'Finance', 'Healthcare', 'Construction',
  'Energy', 'Insurance', 'Government', 'Education',
];

const DIFFERENTIATORS = [
  { title: 'Not wrappers.', desc: 'Every engine has embedded domain knowledge — thousands of reasoning blocks built by specialists, not prompt templates.' },
  { title: 'Not demos.', desc: 'Production systems processing real workloads, 24/7. Battle-tested across adversarial evaluation suites.' },
  { title: 'Not generic.', desc: 'Each vertical gets its own engine with industry-specific logic, terminology, and compliance awareness.' },
  { title: 'Not fragile.', desc: 'Self-healing infrastructure with automatic failover, crash recovery, and distributed redundancy at every layer.' },
];

export default function HomePage() {
  const { isDark, toggle } = useAutoTheme();
  const capSection = useInView();
  const diffSection = useInView();
  const indSection = useInView();
  const ctaSection = useInView();

  return (
    <div className="min-h-screen transition-colors duration-600" style={{ backgroundColor: 'var(--ept-bg)' }}>
      {/* ─── Navigation ─── */}
      <nav className="fixed top-0 w-full z-50 backdrop-blur-2xl border-b transition-colors duration-500" style={{ backgroundColor: 'var(--ept-nav-bg)', borderColor: 'var(--ept-border)' }}>
        <div className="max-w-6xl mx-auto px-6 h-20 flex items-center justify-between">
          <Image src="/logo.png" alt="Echo Prime Technologies" width={320} height={56} className="h-12 w-auto logo-adaptive" priority />
          <div className="hidden md:flex items-center gap-8">
            {['Capabilities', 'Approach', 'Industries', 'Contact'].map(s => (
              <a key={s} href={`#${s.toLowerCase()}`} className="text-sm font-medium transition-colors hover:opacity-100" style={{ color: 'var(--ept-text-secondary)' }}>{s}</a>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={toggle} className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors text-sm" style={{ backgroundColor: 'var(--ept-surface)', color: 'var(--ept-text-secondary)' }}>
              {isDark ? '☀️' : '🌙'}
            </button>
            <a href="#contact" className="hidden md:inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all hover:opacity-90" style={{ backgroundColor: 'var(--ept-accent)', color: '#fff' }}>
              Get Started
            </a>
          </div>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="relative pt-40 pb-32 px-6 mesh-bg overflow-hidden">
        <div className="absolute inset-0" style={{ background: 'var(--ept-hero-gradient)' }} />
        <div className="absolute inset-0 dot-grid opacity-30" />
        <div className="max-w-6xl mx-auto relative">
          <div className="max-w-3xl">
            <div className="animate-fade-up">
              <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full text-xs font-medium mb-8 border backdrop-blur-sm" style={{ backgroundColor: 'var(--ept-accent-glow)', borderColor: 'var(--ept-accent)', color: 'var(--ept-accent)' }}>
                <span className="relative w-2 h-2 rounded-full pulse-ring" style={{ backgroundColor: 'var(--ept-accent)' }} />
                Autonomous Intelligence Systems
              </div>
            </div>

            <h1 className="text-5xl md:text-7xl font-extrabold leading-[1.05] tracking-tight animate-fade-up animate-fade-up-delay-1" style={{ color: 'var(--ept-text)' }}>
              AI that thinks
              <br />
              <span className="gradient-text">like an expert.</span>
            </h1>

            <p className="mt-8 text-xl leading-relaxed max-w-xl animate-fade-up animate-fade-up-delay-2" style={{ color: 'var(--ept-text-secondary)' }}>
              We build domain-specific intelligence engines for industries that can&apos;t afford to be wrong. Over 1,100 engines across 59 verticals. Production-grade. Always on.
            </p>

            <div className="mt-12 flex flex-col sm:flex-row gap-4 animate-fade-up animate-fade-up-delay-3">
              <a href="#capabilities" className="group inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl font-semibold transition-all hover:opacity-90 hover:gap-3" style={{ backgroundColor: 'var(--ept-accent)', color: '#fff' }}>
                See What We Build
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 transition-transform group-hover:translate-x-0.5"><path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" /></svg>
              </a>
              <a href="#approach" className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl border font-semibold transition-all hover:border-opacity-60" style={{ borderColor: 'var(--ept-border)', color: 'var(--ept-text-secondary)' }}>
                Our Approach
              </a>
            </div>
          </div>

          {/* Stats strip */}
          <div className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-px rounded-2xl overflow-hidden glow-sm animate-fade-up animate-fade-up-delay-4" style={{ backgroundColor: 'var(--ept-border)' }}>
            {[
              { value: '1,100+', label: 'Engines Deployed' },
              { value: '59', label: 'Industry Verticals' },
              { value: '<50ms', label: 'Global Response' },
              { value: '99.9%', label: 'Uptime SLA' },
            ].map((s, i) => (
              <div key={i} className="p-8 text-center transition-colors duration-500 relative" style={{ backgroundColor: 'var(--ept-bg)' }}>
                <div className="text-3xl md:text-4xl font-extrabold font-mono gradient-text">{s.value}</div>
                <div className="mt-2 text-xs uppercase tracking-widest font-medium" style={{ color: 'var(--ept-text-muted)' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="accent-line shimmer" />

      {/* ─── Capabilities ─── */}
      <section id="capabilities" className="py-28 px-6" ref={capSection.ref}>
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl mb-16">
            <div className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--ept-accent)' }}>Capabilities</div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight" style={{ color: 'var(--ept-text)' }}>
              What we build
            </h2>
            <p className="mt-5 text-lg leading-relaxed" style={{ color: 'var(--ept-text-secondary)' }}>
              End-to-end autonomous intelligence — from raw data ingestion to production-grade reasoning.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {CAPABILITIES.map((cap, i) => (
              <div
                key={i}
                className={`card-hover p-8 rounded-2xl border transition-all duration-700 ${capSection.visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
                style={{ backgroundColor: 'var(--ept-card-bg)', borderColor: 'var(--ept-card-border)', transitionDelay: `${i * 100}ms` }}
              >
                <div className="text-3xl mb-5 w-14 h-14 rounded-xl flex items-center justify-center font-light" style={{ backgroundColor: 'var(--ept-accent-glow)', color: 'var(--ept-accent)' }}>
                  {cap.icon}
                </div>
                <h3 className="text-lg font-bold mb-3" style={{ color: 'var(--ept-text)' }}>{cap.title}</h3>
                <p className="text-sm leading-relaxed mb-5" style={{ color: 'var(--ept-text-muted)' }}>{cap.description}</p>
                <div className="flex items-baseline gap-2 pt-4 border-t" style={{ borderColor: 'var(--ept-border)' }}>
                  <span className="text-2xl font-extrabold font-mono gradient-text">{cap.stat}</span>
                  <span className="text-xs uppercase tracking-wider font-medium" style={{ color: 'var(--ept-text-muted)' }}>{cap.statLabel}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="accent-line shimmer" />

      {/* ─── Approach (replaces Technology — no secret sauce) ─── */}
      <section id="approach" className="py-28 px-6 mesh-bg" ref={diffSection.ref}>
        <div className="absolute inset-0 dot-grid opacity-20" />
        <div className="max-w-6xl mx-auto relative">
          <div className="max-w-2xl mb-16">
            <div className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--ept-accent)' }}>Our Approach</div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight" style={{ color: 'var(--ept-text)' }}>
              Built different.
            </h2>
            <p className="mt-5 text-lg leading-relaxed" style={{ color: 'var(--ept-text-secondary)' }}>
              Most AI products are thin wrappers around a language model. We build something fundamentally different.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {DIFFERENTIATORS.map((d, i) => (
              <div
                key={i}
                className={`card-hover p-8 rounded-2xl border relative overflow-hidden transition-all duration-700 ${diffSection.visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
                style={{ backgroundColor: 'var(--ept-card-bg)', borderColor: 'var(--ept-card-border)', transitionDelay: `${i * 120}ms` }}
              >
                <div className="absolute top-0 left-0 w-1 h-full rounded-r" style={{ backgroundColor: 'var(--ept-accent)' }} />
                <h3 className="text-2xl font-extrabold mb-3 gradient-text">{d.title}</h3>
                <p className="leading-relaxed" style={{ color: 'var(--ept-text-secondary)' }}>{d.desc}</p>
              </div>
            ))}
          </div>

          <div className={`mt-16 p-10 rounded-2xl border glow-md relative overflow-hidden scan-line transition-all duration-700 ${diffSection.visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`} style={{ backgroundColor: 'var(--ept-card-bg)', borderColor: 'var(--ept-card-border)', transitionDelay: '500ms' }}>
            <div className="grid md:grid-cols-3 gap-8 text-center">
              {[
                { value: '8-step', label: 'Resolution Pipeline', desc: 'Every query goes through multi-stage analysis, not a single prompt.' },
                { value: 'Hybrid', label: 'Retrieval System', desc: 'Precision keyword search combined with semantic understanding.' },
                { value: 'Adversarial', label: 'Evaluation Suite', desc: 'Every engine stress-tested against edge cases before deployment.' },
              ].map((item, i) => (
                <div key={i}>
                  <div className="text-3xl font-extrabold font-mono gradient-text mb-2">{item.value}</div>
                  <div className="text-sm font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--ept-text)' }}>{item.label}</div>
                  <div className="text-sm" style={{ color: 'var(--ept-text-muted)' }}>{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="accent-line shimmer" />

      {/* ─── Industries ─── */}
      <section id="industries" className="py-28 px-6" ref={indSection.ref}>
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl mb-16">
            <div className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--ept-accent)' }}>Industries</div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight" style={{ color: 'var(--ept-text)' }}>
              Built for your vertical.
            </h2>
            <p className="mt-5 text-lg leading-relaxed" style={{ color: 'var(--ept-text-secondary)' }}>
              Every industry gets purpose-built engines with embedded domain expertise. Not one model fine-tuned twelve ways — twelve separate intelligence systems.
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            {INDUSTRIES.map((industry, i) => (
              <div
                key={i}
                className={`card-hover px-6 py-4 rounded-xl border text-sm font-medium cursor-default transition-all duration-500 ${indSection.visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
                style={{ borderColor: 'var(--ept-card-border)', backgroundColor: 'var(--ept-card-bg)', color: 'var(--ept-text-secondary)', transitionDelay: `${i * 60}ms` }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--ept-accent)'; e.currentTarget.style.color = 'var(--ept-text)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--ept-card-border)'; e.currentTarget.style.color = 'var(--ept-text-secondary)'; }}
              >
                {industry}
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="accent-line shimmer" />

      {/* ─── CTA ─── */}
      <section id="contact" className="py-32 px-6 mesh-bg relative" ref={ctaSection.ref}>
        <div className="absolute inset-0 dot-grid opacity-20" />
        <div className={`max-w-3xl mx-auto text-center relative transition-all duration-700 ${ctaSection.visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <h2 className="text-4xl md:text-6xl font-extrabold tracking-tight" style={{ color: 'var(--ept-text)' }}>
            Ready to build<br />
            <span className="gradient-text">something real?</span>
          </h2>
          <p className="mt-6 text-lg leading-relaxed" style={{ color: 'var(--ept-text-secondary)' }}>
            We partner with organizations that need AI systems that actually work. If your industry demands precision, let&apos;s talk.
          </p>
          <div className="mt-12 flex flex-col sm:flex-row gap-4 justify-center">
            <a href="mailto:contact@echo-op.com" className="group inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-semibold text-lg transition-all hover:opacity-90 hover:gap-3" style={{ backgroundColor: 'var(--ept-accent)', color: '#fff' }}>
              Contact Us
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 transition-transform group-hover:translate-x-0.5"><path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" /></svg>
            </a>
            <a href="mailto:contact@echo-op.com" className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl border font-semibold text-lg transition-all" style={{ borderColor: 'var(--ept-border)', color: 'var(--ept-text-secondary)' }}>
              Schedule a Demo
            </a>
          </div>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t py-12 px-6 transition-colors" style={{ borderColor: 'var(--ept-border)' }}>
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <Image src="/logo.png" alt="Echo Prime Technologies" width={240} height={42} className="h-9 w-auto logo-adaptive opacity-70" />
          <div className="flex items-center gap-6 text-xs font-medium" style={{ color: 'var(--ept-text-muted)' }}>
            <span>Midland, Texas</span>
            <span className="w-1 h-1 rounded-full" style={{ backgroundColor: 'var(--ept-text-muted)', opacity: 0.3 }} />
            <a href="mailto:contact@echo-op.com" className="hover:opacity-80 transition-opacity">contact@echo-op.com</a>
            <span className="w-1 h-1 rounded-full" style={{ backgroundColor: 'var(--ept-text-muted)', opacity: 0.3 }} />
            <span>&copy; {new Date().getFullYear()} Echo Prime Technologies</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
