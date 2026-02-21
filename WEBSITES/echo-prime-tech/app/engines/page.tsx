'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '../../lib/auth-context';
import { useTheme } from '../../lib/theme-context';
import {
  getCatalog,
  getPricing,
  createCheckout,
  registerUser,
  isAuthenticated,
  type CatalogResponse,
  type PricingTier,
  type EngineCategory,
} from '../../lib/engine-cloud-api';

// ── Domain metadata: full names, descriptions, capabilities, pricing tier ──

interface DomainInfo {
  name: string;
  description: string;
  capabilities: string[];
  tier: 'Supreme' | 'Critical' | 'Engineering' | 'Standard';
  perQuery: { professional: number; business: number; enterprise: number };
  mergeInto?: string; // single-letter codes merge into a parent
}

const DOMAIN_INFO: Record<string, DomainInfo> = {
  // ═══ Supreme Tier — $12-$30/query ═══
  TX: { name: 'Tax Intelligence', description: 'Federal and state tax law analysis, IRS code interpretation, tax planning strategies, and audit defense.', capabilities: ['IRC code analysis', 'Audit defense briefs', 'Tax planning optimization', 'Multi-entity structuring'], tier: 'Supreme', perQuery: { professional: 30, business: 21, enterprise: 12 } },
  LG: { name: 'Legal Analysis', description: 'Case law research, contract analysis, litigation risk assessment, and regulatory compliance across all practice areas.', capabilities: ['Case law research', 'Contract review', 'Litigation risk scoring', 'Regulatory compliance'], tier: 'Supreme', perQuery: { professional: 30, business: 21, enterprise: 12 } },
  FIN: { name: 'Financial Intelligence', description: 'Financial modeling, risk analysis, portfolio optimization, compliance reporting, and market intelligence.', capabilities: ['Risk modeling', 'Portfolio analysis', 'Compliance reporting', 'Market intelligence'], tier: 'Supreme', perQuery: { professional: 27, business: 18, enterprise: 10.80 } },
  CYBER: { name: 'Cybersecurity', description: 'Threat analysis, vulnerability assessment, incident response planning, and security architecture review.', capabilities: ['Threat intelligence', 'Vulnerability assessment', 'Incident response', 'Security architecture'], tier: 'Supreme', perQuery: { professional: 24, business: 16.80, enterprise: 9 } },
  MED: { name: 'Medical Intelligence', description: 'Clinical decision support, drug interaction analysis, diagnostic reasoning, and medical literature synthesis.', capabilities: ['Clinical decision support', 'Drug interaction analysis', 'Diagnostic reasoning', 'Literature synthesis'], tier: 'Supreme', perQuery: { professional: 30, business: 21, enterprise: 12 } },
  FOREN: { name: 'Forensic Analysis', description: 'Digital forensics, evidence analysis, chain of custody documentation, and expert witness preparation.', capabilities: ['Digital forensics', 'Evidence analysis', 'Chain of custody', 'Expert witness prep'], tier: 'Supreme', perQuery: { professional: 30, business: 21, enterprise: 12 } },
  AGI: { name: 'AGI Systems', description: 'Advanced artificial general intelligence research, cognitive architecture design, and autonomous reasoning systems.', capabilities: ['Cognitive architecture', 'Autonomous reasoning', 'Multi-agent systems', 'Self-improvement loops'], tier: 'Supreme', perQuery: { professional: 30, business: 21, enterprise: 12 } },
  ACCT: { name: 'Accounting & Audit', description: 'GAAP/IFRS compliance, audit procedures, financial statement analysis, and internal controls assessment.', capabilities: ['GAAP/IFRS analysis', 'Audit procedures', 'Financial statements', 'Internal controls'], tier: 'Supreme', perQuery: { professional: 27, business: 18, enterprise: 10.80 } },
  INS: { name: 'Insurance Analysis', description: 'Policy analysis, claims assessment, actuarial reasoning, underwriting support, and regulatory compliance.', capabilities: ['Policy analysis', 'Claims assessment', 'Actuarial reasoning', 'Underwriting support'], tier: 'Supreme', perQuery: { professional: 24, business: 16.80, enterprise: 9 } },
  PRB: { name: 'Probate Law', description: 'Estate administration, will interpretation, trust analysis, inheritance law, and probate court procedures.', capabilities: ['Estate administration', 'Will interpretation', 'Trust analysis', 'Probate procedures'], tier: 'Supreme', perQuery: { professional: 27, business: 18, enterprise: 10.80 } },
  REG: { name: 'Regulatory Compliance', description: 'Multi-agency regulatory analysis, compliance frameworks, reporting requirements, and penalty risk assessment.', capabilities: ['Multi-agency analysis', 'Compliance frameworks', 'Penalty risk assessment', 'Regulatory tracking'], tier: 'Supreme', perQuery: { professional: 27, business: 18, enterprise: 10.80 } },
  DENT: { name: 'Dental Science', description: 'Clinical dentistry knowledge, treatment planning, materials science, oral pathology, and practice management.', capabilities: ['Treatment planning', 'Materials analysis', 'Oral pathology', 'Practice management'], tier: 'Supreme', perQuery: { professional: 24, business: 16.80, enterprise: 9 } },
  DERM: { name: 'Dermatology', description: 'Skin condition analysis, treatment protocols, dermatopathology, cosmetic procedures, and pharmaceutical guidance.', capabilities: ['Condition analysis', 'Treatment protocols', 'Dermatopathology', 'Pharmaceutical guidance'], tier: 'Supreme', perQuery: { professional: 24, business: 16.80, enterprise: 9 } },
  // ═══ Critical Tier — $9-$24/query ═══
  DRL: { name: 'Drilling Engineering', description: 'Well design, drilling fluid analysis, downhole tool selection, directional drilling, and well control procedures.', capabilities: ['Well design', 'Drilling fluid analysis', 'Directional drilling', 'Well control'], tier: 'Critical', perQuery: { professional: 24, business: 16.80, enterprise: 9 } },
  FRAC: { name: 'Fracturing & Completions', description: 'Hydraulic fracturing design, completion optimization, proppant selection, and stimulation treatment analysis.', capabilities: ['Frac design', 'Completion optimization', 'Proppant selection', 'Stimulation analysis'], tier: 'Critical', perQuery: { professional: 24, business: 16.80, enterprise: 9 } },
  OFE: { name: 'Oilfield Equipment', description: 'Equipment specification, maintenance scheduling, failure analysis, and operational safety for upstream oil and gas.', capabilities: ['Equipment specification', 'Failure analysis', 'Maintenance planning', 'Safety compliance'], tier: 'Critical', perQuery: { professional: 21, business: 15, enterprise: 8.40 } },
  PROD: { name: 'Production Engineering', description: 'Well production optimization, artificial lift selection, flow assurance, and decline curve analysis.', capabilities: ['Production optimization', 'Artificial lift', 'Flow assurance', 'Decline analysis'], tier: 'Critical', perQuery: { professional: 21, business: 15, enterprise: 8.40 } },
  ENRG: { name: 'Energy Systems', description: 'Power generation, grid management, renewable energy analysis, nuclear systems, and energy policy.', capabilities: ['Power generation', 'Grid management', 'Renewable analysis', 'Energy policy'], tier: 'Critical', perQuery: { professional: 21, business: 15, enterprise: 8.40 } },
  AERO: { name: 'Aerospace Engineering', description: 'Aircraft systems, propulsion, aerodynamics, avionics, structural analysis, and aviation safety.', capabilities: ['Aircraft systems', 'Propulsion analysis', 'Structural engineering', 'Aviation safety'], tier: 'Critical', perQuery: { professional: 21, business: 15, enterprise: 8.40 } },
  CHEM: { name: 'Chemical Engineering', description: 'Process design, reaction kinetics, thermodynamics, materials science, and chemical safety analysis.', capabilities: ['Process design', 'Reaction kinetics', 'Materials science', 'Chemical safety'], tier: 'Critical', perQuery: { professional: 18, business: 13.20, enterprise: 7.20 } },
  LM: { name: 'Land & Minerals', description: 'Title examination, mineral rights analysis, lease interpretation, right-of-way, and chain of title research.', capabilities: ['Title examination', 'Mineral rights', 'Lease interpretation', 'Chain of title'], tier: 'Critical', perQuery: { professional: 27, business: 18, enterprise: 10.80 } },
  CRYPTO: { name: 'Digital Assets & Cryptocurrency', description: 'Blockchain analysis, DeFi protocol evaluation, smart contract review, and digital asset compliance.', capabilities: ['Blockchain analysis', 'DeFi evaluation', 'Smart contract review', 'Asset compliance'], tier: 'Critical', perQuery: { professional: 21, business: 15, enterprise: 8.40 } },
  BIO: { name: 'Biotechnology', description: 'Genomics, proteomics, bioinformatics, drug discovery, and bioprocess engineering.', capabilities: ['Genomics analysis', 'Drug discovery', 'Bioinformatics', 'Bioprocess engineering'], tier: 'Critical', perQuery: { professional: 18, business: 13.20, enterprise: 7.20 } },
  // ═══ Engineering Tier — $6-$18/query ═══
  MECH: { name: 'Mechanical Engineering', description: 'Structural analysis, thermodynamics, fluid dynamics, machine design, and manufacturing processes.', capabilities: ['Structural analysis', 'Thermodynamics', 'Machine design', 'Manufacturing'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  AUTO: { name: 'Automotive Engineering', description: 'Vehicle systems, powertrain, diagnostics, emissions, EV technology, and autonomous driving systems.', capabilities: ['Vehicle diagnostics', 'Powertrain analysis', 'EV technology', 'Emissions compliance'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  EE: { name: 'Electrical Engineering', description: 'Circuit design, power systems, control theory, signal processing, and embedded systems.', capabilities: ['Circuit design', 'Power systems', 'Control theory', 'Signal processing'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  ELECT: { name: 'Electronics Engineering', description: 'PCB design, semiconductor physics, digital logic, FPGA/ASIC, and RF engineering.', capabilities: ['PCB design', 'Semiconductor physics', 'FPGA/ASIC design', 'RF engineering'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  HVAC: { name: 'HVAC Engineering', description: 'Heating, ventilation, air conditioning, refrigeration, energy efficiency, and building climate control.', capabilities: ['System design', 'Load calculations', 'Energy efficiency', 'Refrigeration'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  RAIL: { name: 'Railroad Engineering', description: 'Track design, locomotive systems, signaling, freight logistics, and railway safety standards.', capabilities: ['Track design', 'Locomotive systems', 'Signaling', 'Safety standards'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  CONST: { name: 'Construction Engineering', description: 'Structural design, building codes, project management, cost estimation, and construction safety.', capabilities: ['Structural design', 'Code compliance', 'Cost estimation', 'Safety planning'], tier: 'Engineering', perQuery: { professional: 18, business: 13.20, enterprise: 7.20 } },
  ARCH: { name: 'Architecture & Design', description: 'Building design, urban planning, sustainable architecture, building information modeling, and design standards.', capabilities: ['Building design', 'Urban planning', 'Sustainable design', 'BIM analysis'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  FIRMWARE: { name: 'Firmware Engineering', description: 'Embedded systems programming, RTOS, microcontroller design, IoT protocols, and hardware-software integration.', capabilities: ['Embedded systems', 'RTOS design', 'IoT protocols', 'HW/SW integration'], tier: 'Engineering', perQuery: { professional: 16.80, business: 12, enterprise: 6 } },
  CARP: { name: 'Carpentry & Woodworking', description: 'Joinery techniques, structural framing, cabinetry, wood species selection, and finishing methods.', capabilities: ['Joinery techniques', 'Structural framing', 'Cabinetry design', 'Finishing methods'], tier: 'Engineering', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  // ═══ Standard Tier — $2.50-$15/query ═══
  AIML: { name: 'AI & Machine Learning', description: 'Model architecture, training optimization, MLOps, neural network design, and AI system evaluation.', capabilities: ['Model architecture', 'Training optimization', 'MLOps pipelines', 'System evaluation'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  BIZ: { name: 'Business Strategy', description: 'Market analysis, competitive intelligence, business planning, M&A evaluation, and organizational design.', capabilities: ['Market analysis', 'Competitive intelligence', 'Business planning', 'M&A evaluation'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  DCOM: { name: 'Digital Commerce', description: 'E-commerce strategy, payment systems, marketplace optimization, digital marketing, and conversion analytics.', capabilities: ['E-commerce strategy', 'Payment systems', 'Marketplace optimization', 'Conversion analytics'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  ENT: { name: 'Enterprise Systems', description: 'ERP integration, CRM optimization, enterprise architecture, IT governance, and digital transformation.', capabilities: ['ERP integration', 'CRM optimization', 'IT governance', 'Digital transformation'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  MATH: { name: 'Mathematics & Statistics', description: 'Advanced mathematics, statistical analysis, probability theory, optimization, and computational methods.', capabilities: ['Statistical analysis', 'Optimization', 'Probability theory', 'Computational methods'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  LING: { name: 'Linguistics & NLP', description: 'Natural language processing, computational linguistics, translation, sentiment analysis, and text mining.', capabilities: ['NLP pipelines', 'Sentiment analysis', 'Translation', 'Text mining'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  FOOD: { name: 'Food Safety & Science', description: 'Food safety regulations, HACCP planning, nutritional analysis, food processing, and quality assurance.', capabilities: ['HACCP planning', 'Nutritional analysis', 'Food processing', 'Quality assurance'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  ENVIRO: { name: 'Environmental Science', description: 'Environmental impact assessment, remediation, air/water quality, waste management, and sustainability.', capabilities: ['Impact assessment', 'Remediation planning', 'Air/water quality', 'Sustainability'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  GAME: { name: 'Game Development', description: 'Game engine architecture, graphics programming, physics simulation, multiplayer networking, and level design.', capabilities: ['Engine architecture', 'Graphics programming', 'Physics simulation', 'Multiplayer systems'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  EDU: { name: 'Education & Training', description: 'Curriculum design, learning management, assessment development, educational technology, and pedagogy.', capabilities: ['Curriculum design', 'Assessment development', 'EdTech integration', 'Learning analytics'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  HIST: { name: 'Historical Analysis', description: 'Historical research, archival analysis, historiography, cultural studies, and chronological reasoning.', capabilities: ['Archival research', 'Historiography', 'Cultural analysis', 'Period expertise'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  GEOL: { name: 'Geology & Geoscience', description: 'Geological surveys, mineralogy, stratigraphy, petroleum geology, and geophysical analysis.', capabilities: ['Geological surveys', 'Petroleum geology', 'Stratigraphy', 'Geophysical analysis'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  ASTRO: { name: 'Astronomy & Space Science', description: 'Astrophysics, orbital mechanics, space systems, satellite design, and planetary science.', capabilities: ['Orbital mechanics', 'Space systems', 'Satellite design', 'Planetary science'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  HOSP: { name: 'Hospitality & Tourism', description: 'Hotel operations, restaurant management, event planning, tourism strategy, and guest experience.', capabilities: ['Operations management', 'Revenue optimization', 'Event planning', 'Guest experience'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  AGRI: { name: 'Agriculture', description: 'Crop science, precision agriculture, soil analysis, irrigation systems, and agricultural economics.', capabilities: ['Crop science', 'Precision agriculture', 'Soil analysis', 'Agricultural economics'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  DIET: { name: 'Dietary & Nutrition Science', description: 'Clinical nutrition, dietary planning, metabolic analysis, sports nutrition, and functional foods.', capabilities: ['Clinical nutrition', 'Dietary planning', 'Metabolic analysis', 'Sports nutrition'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  FOREST: { name: 'Forestry Science', description: 'Forest management, silviculture, timber analysis, wildfire prevention, and ecosystem conservation.', capabilities: ['Forest management', 'Timber analysis', 'Wildfire prevention', 'Conservation'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  FASH: { name: 'Fashion & Textiles', description: 'Textile engineering, fashion design, supply chain, material science, and trend analysis.', capabilities: ['Textile engineering', 'Material science', 'Supply chain', 'Trend analysis'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  AQUA: { name: 'Aquaculture & Marine Biology', description: 'Marine ecosystems, fish farming, water quality management, coral reef science, and ocean engineering.', capabilities: ['Marine ecosystems', 'Aquaculture systems', 'Water quality', 'Ocean engineering'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  ET: { name: 'Echo Talk Personality AI', description: 'Conversational AI personality engines, emotion detection, cognitive modeling, and voice synthesis integration.', capabilities: ['Personality modeling', 'Emotion detection', 'Cognitive engines', 'Voice synthesis'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  INT: { name: 'Intelligence & Analytics', description: 'Data intelligence, OSINT, pattern recognition, predictive analytics, and decision support systems.', capabilities: ['OSINT analysis', 'Pattern recognition', 'Predictive analytics', 'Decision support'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  GEO: { name: 'Geospatial Analysis', description: 'GIS mapping, spatial analysis, remote sensing, terrain modeling, and location intelligence.', capabilities: ['GIS mapping', 'Spatial analysis', 'Remote sensing', 'Location intelligence'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  GOV: { name: 'Governance & Policy', description: 'Policy analysis, government compliance, public administration, regulatory affairs, and civic technology.', capabilities: ['Policy analysis', 'Government compliance', 'Public administration', 'Civic technology'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  SYN: { name: 'Synthesis Engines', description: 'Multi-domain synthesis, cross-disciplinary analysis, knowledge fusion, and integrated reasoning.', capabilities: ['Multi-domain synthesis', 'Knowledge fusion', 'Cross-disciplinary analysis', 'Integrated reasoning'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  GS: { name: 'GS343 Error Healing', description: 'Automated error detection, self-healing systems, template-based recovery, and fault tolerance.', capabilities: ['Error detection', 'Self-healing', 'Template recovery', 'Fault tolerance'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  BLD: { name: 'Building Science', description: 'Building envelope design, energy performance, indoor air quality, moisture management, and building codes.', capabilities: ['Envelope design', 'Energy performance', 'Air quality', 'Code compliance'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  FTUNE: { name: 'AI Fine-Tuning', description: 'Model fine-tuning strategies, dataset curation, training pipelines, and performance benchmarking.', capabilities: ['Fine-tuning strategy', 'Dataset curation', 'Training pipelines', 'Benchmarking'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  CON: { name: 'Consulting Intelligence', description: 'Management consulting frameworks, strategy analysis, operational improvement, and change management.', capabilities: ['Strategy frameworks', 'Operational improvement', 'Change management', 'Performance analysis'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  // ═══ Merge targets — single-letter/duplicate codes fold into parent domains ═══
  PB: { name: 'Permian Basin Operations', description: 'Permian Basin-specific oil and gas operations, well data, production analysis, and regional geology.', capabilities: ['Basin analysis', 'Well data', 'Production analysis', 'Regional geology'], tier: 'Critical', perQuery: { professional: 21, business: 15, enterprise: 8.40 } },
  GSP: { name: 'Geospatial Processing', description: 'Advanced geospatial data processing, coordinate systems, projection analysis, and spatial queries.', capabilities: ['Data processing', 'Projections', 'Spatial queries', 'Coordinate systems'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  AGR: { name: 'Agricultural Research', description: 'Agricultural research methods, crop genetics, pest management, and sustainable farming practices.', capabilities: ['Crop genetics', 'Pest management', 'Research methods', 'Sustainable farming'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  SYNT: { name: 'Synthesis Research', description: 'Advanced cross-domain synthesis and knowledge integration.', capabilities: ['Cross-domain synthesis', 'Knowledge integration'], tier: 'Standard', perQuery: { professional: 9, business: 6, enterprise: 3 } },
  // Single-letter codes — display with expanded names
  R: { name: 'Rendering & Visualization', description: 'Real-time rendering, ray tracing, 3D visualization, shader programming, and GPU compute.', capabilities: ['Real-time rendering', 'Ray tracing', '3D visualization', 'Shader programming'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  E: { name: 'Energy Research', description: 'Cross-cutting energy research, grid analysis, energy storage, and transition planning.', capabilities: ['Grid analysis', 'Energy storage', 'Transition planning', 'Research synthesis'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  S: { name: 'Security & Defense', description: 'Security analysis, defense systems, threat modeling, and protective intelligence.', capabilities: ['Threat modeling', 'Defense systems', 'Protective intelligence', 'Security analysis'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  P: { name: 'Physics & Engineering Research', description: 'Applied physics, materials research, experimental methods, and engineering science.', capabilities: ['Applied physics', 'Materials research', 'Experimental methods', 'Engineering science'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  I: { name: 'Information Systems', description: 'Information architecture, data management, systems integration, and knowledge management.', capabilities: ['Information architecture', 'Data management', 'Systems integration', 'Knowledge management'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  W: { name: 'Water & Environmental Engineering', description: 'Water treatment, hydrology, watershed management, and environmental remediation.', capabilities: ['Water treatment', 'Hydrology', 'Watershed management', 'Remediation'], tier: 'Standard', perQuery: { professional: 12, business: 9, enterprise: 4.80 } },
  G: { name: 'Graphics Engineering', description: 'Computer graphics, image processing, visual computing, and display technology.', capabilities: ['Computer graphics', 'Image processing', 'Visual computing', 'Display technology'], tier: 'Standard', perQuery: { professional: 15, business: 10.80, enterprise: 5.40 } },
  L: { name: 'Legal Research', description: 'Specialized legal research and precedent analysis.', capabilities: ['Legal research', 'Precedent analysis'], tier: 'Supreme', perQuery: { professional: 27, business: 18, enterprise: 10.80 } },
};

function getDomainInfo(code: string): DomainInfo {
  return DOMAIN_INFO[code] || {
    name: code,
    description: 'Specialized knowledge engine with pre-compiled doctrine blocks.',
    capabilities: ['Domain analysis', 'Expert reasoning'],
    tier: 'Standard' as const,
    perQuery: { professional: 9, business: 6, enterprise: 3 },
  };
}

// ── Tier classification ──

const TIER_GROUPS: { label: string; color: string; glow: string; tiers: string[] }[] = [
  { label: 'Supreme', color: '#f59e0b', glow: '#f59e0b33', tiers: ['Supreme'] },
  { label: 'Critical', color: '#ef4444', glow: '#ef444433', tiers: ['Critical'] },
  { label: 'Engineering', color: '#6366f1', glow: '#6366f133', tiers: ['Engineering'] },
  { label: 'Standard', color: '#10b981', glow: '#10b98133', tiers: ['Standard'] },
];

function getTierGroup(category: string): typeof TIER_GROUPS[number] {
  const info = getDomainInfo(category);
  const tierGroup = TIER_GROUPS.find(g => g.tiers.includes(info.tier));
  return tierGroup || TIER_GROUPS[3];
}

export default function EnginesPage() {
  const { user } = useAuth();
  const { isDark } = useTheme();
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [pricing, setPricing] = useState<PricingTier[]>([]);
  const [search, setSearch] = useState('');
  const [expandedGroup, setExpandedGroup] = useState<string | null>('Supreme');
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([
      getCatalog().then(setCatalog),
      getPricing().then(p => setPricing(p.tiers)),
    ]).finally(() => setLoading(false));
  }, []);

  const totalEngines = catalog?.total_engines || 932;
  const totalDoctrines = catalog?.total_doctrines || 35331;
  const categories = catalog?.categories || [];
  const totalCategories = categories.length || 65;

  // Group categories by tier
  const grouped = useMemo(() => {
    const q = search.toLowerCase();
    const filtered = search
      ? categories.filter(c => {
        const info = getDomainInfo(c.name);
        return c.name.toLowerCase().includes(q)
          || info.name.toLowerCase().includes(q)
          || info.description.toLowerCase().includes(q)
          || info.capabilities.some(cap => cap.toLowerCase().includes(q))
          || c.description?.toLowerCase().includes(q);
      })
      : categories;

    const groups: Record<string, EngineCategory[]> = { Supreme: [], Critical: [], Engineering: [], Standard: [] };
    for (const cat of filtered) {
      const tier = getTierGroup(cat.name);
      groups[tier.label].push(cat);
    }
    return groups;
  }, [categories, search]);

  const handleRegister = async () => {
    if (!user?.email) return;
    setRegistering(true);
    try {
      await registerUser(user.email, user.displayName || undefined);
      window.location.href = '/sentinel';
    } catch {
      alert('Registration failed. You may already have an account — try Sentinel directly.');
    } finally {
      setRegistering(false);
    }
  };

  const handleCheckout = async (tier: string) => {
    setUpgrading(tier);
    try {
      const { checkout_url } = await createCheckout(
        tier.toLowerCase() as 'professional' | 'business' | 'enterprise',
        `${window.location.origin}/sentinel?upgraded=true`,
        window.location.href,
      );
      window.location.href = checkout_url;
    } catch {
      alert('Checkout failed. Please try again.');
      setUpgrading(null);
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--ept-bg)' }}>
      {/* Nav */}
      <nav className="border-b px-6 py-4 flex items-center justify-between" style={{ borderColor: 'var(--ept-border)', backgroundColor: 'var(--ept-card-bg)' }}>
        <Link href="/">
          <Image src={isDark ? '/logo-night.png' : '/logo-day.png'} alt="EPT" width={400} height={260} className="w-[160px] md:w-[200px] h-auto" style={{ mixBlendMode: isDark ? 'screen' : 'multiply' }} priority />
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/sentinel" className="text-sm font-semibold px-4 py-2 rounded-lg transition-all hover:opacity-90" style={{ backgroundColor: '#6366f1', color: '#fff' }}>
            Open Sentinel
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="relative overflow-hidden" style={{ background: isDark ? 'linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%)' : 'linear-gradient(180deg, #f0f4ff 0%, #fff 100%)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-6" style={{ backgroundColor: '#6366f120', color: '#818cf8', border: '1px solid #6366f140' }}>
            Engine Intelligence Catalog
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold mb-4" style={{ color: 'var(--ept-text)' }}>
            <span style={{ background: 'linear-gradient(135deg, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              {totalEngines.toLocaleString()}
            </span>{' '}
            Engines
            <span className="text-lg md:text-2xl font-bold ml-3" style={{ color: 'var(--ept-text-muted)' }}>
              3,279 planned
            </span>
          </h1>
          <p className="text-lg md:text-xl max-w-3xl mx-auto mb-8" style={{ color: 'var(--ept-text-secondary)' }}>
            {totalCategories} live domains. {totalDoctrines.toLocaleString()} pre-compiled doctrine blocks. Court-defensible. Zero hallucination.
            Every response grounded in expert knowledge with deterministic audit trails.
          </p>
          <div className="flex flex-wrap justify-center gap-4 md:gap-6 mb-10">
            {[
              { label: 'Live Engines', value: totalEngines.toLocaleString(), icon: '⚡' },
              { label: 'Planned Total', value: '3,279', icon: '🚀' },
              { label: 'Domains', value: String(totalCategories), icon: '🏛️' },
              { label: 'Doctrines', value: totalDoctrines.toLocaleString(), icon: '📋' },
              { label: 'Encryption', value: 'AES-256', icon: '🔒' },
            ].map(s => (
              <div key={s.label} className="px-5 py-3 rounded-xl" style={{ backgroundColor: 'var(--ept-surface)', border: '1px solid var(--ept-border)' }}>
                <div className="text-2xl font-extrabold font-mono" style={{ color: 'var(--ept-text)' }}>{s.icon} {s.value}</div>
                <div className="text-xs mt-1" style={{ color: 'var(--ept-text-muted)' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Search + Filter */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="relative mb-8">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: 'var(--ept-text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search engines by domain, category, or keyword..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 rounded-xl text-sm"
            style={{
              backgroundColor: 'var(--ept-surface)',
              border: '1px solid var(--ept-border)',
              color: 'var(--ept-text)',
              outline: 'none',
            }}
          />
        </div>

        {/* Category Grid by Tier */}
        {loading ? (
          <div className="text-center py-20" style={{ color: 'var(--ept-text-muted)' }}>
            <div className="inline-block w-8 h-8 rounded-full border-2 border-t-transparent animate-spin mb-4" style={{ borderColor: '#6366f1', borderTopColor: 'transparent' }} />
            <p>Loading engine catalog...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {TIER_GROUPS.map(tier => {
              const cats = grouped[tier.label] || [];
              if (cats.length === 0) return null;
              const isExpanded = expandedGroup === tier.label;
              const totalInTier = cats.reduce((sum, c) => sum + c.engines, 0);

              return (
                <div key={tier.label} className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${tier.color}30`, backgroundColor: 'var(--ept-card-bg)' }}>
                  <button
                    onClick={() => setExpandedGroup(isExpanded ? null : tier.label)}
                    className="w-full flex items-center justify-between px-6 py-4 text-left transition-all"
                    style={{ backgroundColor: `${tier.color}08` }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: tier.color, boxShadow: `0 0 8px ${tier.glow}` }} />
                      <span className="text-lg font-bold" style={{ color: 'var(--ept-text)' }}>{tier.label} Tier</span>
                      <span className="text-xs px-2 py-0.5 rounded-full font-mono" style={{ backgroundColor: `${tier.color}20`, color: tier.color }}>
                        {cats.length} categories / {totalInTier} engines
                      </span>
                    </div>
                    <svg className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} style={{ color: 'var(--ept-text-muted)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>

                  {isExpanded && (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
                      {cats.map(cat => {
                        const info = getDomainInfo(cat.name);
                        const depthScore = cat.knowledge_depth
                          ? Math.min(5, Math.max(1, Math.round(cat.knowledge_depth / 250)))
                          : 3;
                        return (
                          <div key={cat.name} className="p-5 rounded-xl transition-all hover:scale-[1.01]" style={{ backgroundColor: 'var(--ept-surface)', border: '1px solid var(--ept-border)' }}>
                            <div className="flex items-start justify-between mb-1.5">
                              <div>
                                <h3 className="text-sm font-bold leading-tight" style={{ color: 'var(--ept-text)' }}>{info.name}</h3>
                                <span className="text-[10px] font-mono" style={{ color: 'var(--ept-text-muted)' }}>{cat.name}</span>
                              </div>
                              <span className="text-xs font-mono px-2 py-0.5 rounded flex-shrink-0" style={{ backgroundColor: `${tier.color}15`, color: tier.color }}>
                                {cat.engines} engines
                              </span>
                            </div>
                            <p className="text-xs mb-3 leading-relaxed" style={{ color: 'var(--ept-text-muted)' }}>
                              {info.description}
                            </p>
                            {/* Capabilities */}
                            <div className="flex flex-wrap gap-1 mb-3">
                              {info.capabilities.slice(0, 4).map(cap => (
                                <span key={cap} className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${tier.color}10`, color: tier.color, border: `1px solid ${tier.color}20` }}>
                                  {cap}
                                </span>
                              ))}
                            </div>
                            <div className="flex items-center justify-between">
                              <div className="text-[10px]" style={{ color: 'var(--ept-text-muted)' }}>
                                <span title="Enterprise price">${info.perQuery.enterprise}</span>
                                <span className="mx-1">—</span>
                                <span title="Professional price">${info.perQuery.professional}</span>
                                <span className="ml-0.5">/query</span>
                              </div>
                              <div className="flex gap-0.5" title={`Knowledge depth: ${cat.knowledge_depth || 0} doctrines`}>
                                {[1, 2, 3, 4, 5].map(i => (
                                  <div key={i} className="w-1.5 h-3 rounded-sm" style={{
                                    backgroundColor: i <= depthScore ? tier.color : 'var(--ept-border)',
                                  }} />
                                ))}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ═══ Coming Soon / Under Construction ═══ */}
        <div className="mt-12 rounded-2xl overflow-hidden" style={{ border: '1px solid #8b5cf620', backgroundColor: 'var(--ept-card-bg)' }}>
          <div className="px-6 py-4" style={{ backgroundColor: '#8b5cf608' }}>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full animate-pulse" style={{ backgroundColor: '#8b5cf6', boxShadow: '0 0 8px #8b5cf633' }} />
              <span className="text-lg font-bold" style={{ color: 'var(--ept-text)' }}>Under Construction</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono" style={{ backgroundColor: '#8b5cf620', color: '#8b5cf6' }}>
                2,347 engines planned
              </span>
            </div>
            <p className="text-xs mt-2 ml-6" style={{ color: 'var(--ept-text-muted)' }}>
              Actively building toward 3,279 engines across 178 domains. New engines deploy daily via automated build pipeline.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3 p-6">
            {[
              { code: 'NUC', name: 'Nuclear Engineering', desc: 'Reactor design, radiation safety, fuel cycle analysis, and nuclear waste management.', engines: 15 },
              { code: 'MINE', name: 'Mining Engineering', desc: 'Mine planning, extraction methods, mineral processing, and mine safety.', engines: 15 },
              { code: 'TELE', name: 'Telecommunications', desc: '5G/6G networks, fiber optics, satellite communications, and spectrum management.', engines: 15 },
              { code: 'SCM', name: 'Supply Chain Management', desc: 'Logistics optimization, inventory management, procurement, and demand forecasting.', engines: 15 },
              { code: 'RENEW', name: 'Renewable Energy', desc: 'Solar, wind, hydro, geothermal systems design, and energy storage.', engines: 15 },
              { code: 'WELD', name: 'Welding Engineering', desc: 'Welding procedures, metallurgy, inspection methods, and code compliance.', engines: 15 },
              { code: 'SPORT', name: 'Sports Science', desc: 'Biomechanics, performance analysis, injury prevention, and training optimization.', engines: 12 },
              { code: 'WEATHER', name: 'Meteorology', desc: 'Weather prediction, climate modeling, atmospheric science, and storm analysis.', engines: 12 },
              { code: 'MUSIC', name: 'Music Theory & Production', desc: 'Composition, audio engineering, acoustics, and music information retrieval.', engines: 10 },
              { code: 'VET', name: 'Veterinary Science', desc: 'Animal health, diagnostics, surgical procedures, and pharmacology.', engines: 12 },
              { code: 'MARINE', name: 'Marine Engineering', desc: 'Naval architecture, propulsion systems, offshore structures, and maritime safety.', engines: 15 },
              { code: 'PHARM', name: 'Pharmaceutical Science', desc: 'Drug development, pharmacokinetics, clinical trials, and regulatory submissions.', engines: 15 },
              { code: 'RE', name: 'Real Estate Intelligence', desc: 'Property valuation, market analysis, title research, and investment modeling.', engines: 12 },
              { code: 'ROBOT', name: 'Robotics & Automation', desc: 'Robot design, control systems, computer vision, and industrial automation.', engines: 15 },
              { code: 'QUANT', name: 'Quantitative Finance', desc: 'Algorithmic trading, risk modeling, derivatives pricing, and portfolio optimization.', engines: 12 },
              { code: 'PSYCH', name: 'Psychology & Cognitive Science', desc: 'Clinical psychology, cognitive modeling, behavioral analysis, and neuropsychology.', engines: 10 },
            ].map(d => (
              <div key={d.code} className="p-4 rounded-xl relative overflow-hidden" style={{ backgroundColor: 'var(--ept-surface)', border: '1px solid var(--ept-border)', opacity: 0.85 }}>
                <div className="absolute top-2 right-2 text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: '#8b5cf620', color: '#8b5cf6' }}>
                  BUILDING
                </div>
                <h4 className="text-xs font-bold mb-1" style={{ color: 'var(--ept-text)' }}>{d.name}</h4>
                <span className="text-[10px] font-mono" style={{ color: 'var(--ept-text-muted)' }}>{d.code}</span>
                <p className="text-[10px] mt-1.5 leading-relaxed" style={{ color: 'var(--ept-text-muted)' }}>{d.desc}</p>
                <div className="text-[10px] mt-2 font-mono" style={{ color: '#8b5cf6' }}>~{d.engines} engines planned</div>
              </div>
            ))}
          </div>
        </div>

        {/* Domain Pricing Explainer */}
        <div className="mt-12 p-6 rounded-2xl" style={{ backgroundColor: 'var(--ept-surface)', border: '1px solid var(--ept-border)' }}>
          <h3 className="text-base font-bold mb-3" style={{ color: 'var(--ept-text)' }}>How Domain Pricing Works</h3>
          <p className="text-sm mb-4" style={{ color: 'var(--ept-text-secondary)' }}>
            Each subscription plan includes a monthly query allocation. The per-query cost varies by domain complexity — specialized domains like Tax, Legal, and Medical cost more than general domains because they require deeper doctrine analysis and carry higher liability standards.
          </p>
          <div className="grid md:grid-cols-4 gap-4">
            {[
              { tier: 'Supreme', color: '#f59e0b', range: '$12 — $30', desc: 'Tax, Legal, Medical, Forensic, Insurance — highest liability, deepest doctrine' },
              { tier: 'Critical', color: '#ef4444', range: '$7.20 — $27', desc: 'Drilling, Fracturing, Energy, Aerospace, Crypto — safety-critical engineering' },
              { tier: 'Engineering', color: '#6366f1', range: '$4.80 — $18', desc: 'Mechanical, Electrical, HVAC, Construction — professional engineering domains' },
              { tier: 'Standard', color: '#10b981', range: '$2.50 — $15', desc: 'Business, Education, Agriculture, AI/ML — broad knowledge domains' },
            ].map(t => (
              <div key={t.tier} className="p-4 rounded-xl" style={{ border: `1px solid ${t.color}30` }}>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: t.color }} />
                  <span className="text-xs font-bold" style={{ color: t.color }}>{t.tier}</span>
                </div>
                <div className="text-lg font-bold font-mono mb-1" style={{ color: 'var(--ept-text)' }}>{t.range}</div>
                <div className="text-[10px]" style={{ color: 'var(--ept-text-muted)' }}>{t.desc}</div>
              </div>
            ))}
          </div>
          <p className="text-xs mt-4" style={{ color: 'var(--ept-text-muted)' }}>
            Per-query costs are deducted from your monthly plan. Enterprise tier gets the lowest per-query rate. Free tier includes 3 queries at no cost across all domains.
          </p>
        </div>

        {/* Pricing Section */}
        <div className="mt-20 mb-16">
          <div className="text-center mb-12">
            <div className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: '#818cf8' }}>Pricing</div>
            <h2 className="text-3xl md:text-4xl font-extrabold" style={{ color: 'var(--ept-text)' }}>
              Zero hallucination starts free
            </h2>
            <p className="mt-3 text-sm max-w-2xl mx-auto" style={{ color: 'var(--ept-text-secondary)' }}>
              Court-defensible AI that replaces $300-500/hour professionals. Every tier includes encrypted reports, deterministic audit trails, and full doctrine citations.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
            {pricing.length > 0 ? pricing.map(tier => {
              const tierKey = tier.name.toLowerCase();
              const isFree = tier.price === 0;
              return (
                <div key={tier.name} className="relative p-6 rounded-2xl transition-all" style={{
                  backgroundColor: 'var(--ept-card-bg)',
                  border: tier.popular ? '2px solid #6366f1' : '1px solid var(--ept-border)',
                  boxShadow: tier.popular ? '0 0 30px #6366f122' : 'none',
                }}>
                  {tier.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold" style={{ backgroundColor: '#6366f1', color: '#fff' }}>
                      Most Popular
                    </div>
                  )}
                  <h3 className="text-base font-bold mt-1" style={{ color: 'var(--ept-text)' }}>{tier.name}</h3>
                  <div className="mt-3 mb-1">
                    <span className="text-3xl font-extrabold font-mono" style={{ color: 'var(--ept-text)' }}>
                      {isFree ? 'Free' : `$${tier.price}`}
                    </span>
                    {!isFree && <span className="text-sm" style={{ color: 'var(--ept-text-muted)' }}>/mo</span>}
                  </div>
                  <div className="text-xs mb-4" style={{ color: 'var(--ept-text-muted)' }}>
                    {tier.queries.toLocaleString()} queries/month
                  </div>
                  <ul className="space-y-2 mb-6">
                    {tier.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs" style={{ color: 'var(--ept-text-secondary)' }}>
                        <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: '#10b981' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                  {isFree ? (
                    isAuthenticated() ? (
                      <Link href="/sentinel" className="block text-center py-2.5 rounded-lg text-sm font-semibold" style={{ border: '1px solid var(--ept-border)', color: 'var(--ept-text-secondary)' }}>
                        Open Sentinel
                      </Link>
                    ) : user?.email ? (
                      <button
                        onClick={handleRegister}
                        disabled={registering}
                        className="w-full py-2.5 rounded-lg text-sm font-semibold transition-all"
                        style={{ backgroundColor: '#6366f120', color: '#818cf8', border: '1px solid #6366f140' }}
                      >
                        {registering ? 'Registering...' : 'Activate Free'}
                      </button>
                    ) : (
                      <Link href="/signup" className="block text-center py-2.5 rounded-lg text-sm font-semibold" style={{ backgroundColor: '#6366f120', color: '#818cf8', border: '1px solid #6366f140' }}>
                        Get Started
                      </Link>
                    )
                  ) : (
                    <button
                      onClick={() => handleCheckout(tierKey)}
                      disabled={upgrading !== null}
                      className="w-full py-2.5 rounded-lg text-sm font-semibold transition-all"
                      style={{
                        backgroundColor: tier.popular ? '#6366f1' : 'transparent',
                        color: tier.popular ? '#fff' : '#818cf8',
                        border: tier.popular ? 'none' : '1px solid #6366f1',
                        cursor: upgrading ? 'wait' : 'pointer',
                      }}
                    >
                      {upgrading === tierKey ? 'Redirecting...' : `Subscribe`}
                    </button>
                  )}
                </div>
              );
            }) : (
              /* Static fallback pricing */
              [
                { name: 'Free', price: 0, queries: 3, features: ['3 queries/month', 'All 932 engines', 'Court-defensible analysis'], popular: false },
                { name: 'Professional', price: 3000, queries: 250, features: ['250 queries/month', 'All 65 domains', 'Encrypted reports', 'Quarterly: $7,500 · Annual: $25,000'], popular: false },
                { name: 'Business', price: 9000, queries: 1000, features: ['1,000 queries/month', 'Priority routing', 'Full reports', 'Quarterly: $22,500 · Annual: $75,000'], popular: true },
                { name: 'Enterprise', price: 30000, queries: 5000, features: ['5,000 queries/month', 'Custom training', 'Dedicated AM', 'Quarterly: $75,000 · Annual: $250,000'], popular: false },
              ].map(tier => (
                <div key={tier.name} className="p-6 rounded-2xl" style={{
                  backgroundColor: 'var(--ept-card-bg)',
                  border: tier.popular ? '2px solid #6366f1' : '1px solid var(--ept-border)',
                }}>
                  {tier.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold" style={{ backgroundColor: '#6366f1', color: '#fff' }}>Popular</div>
                  )}
                  <h3 className="text-base font-bold" style={{ color: 'var(--ept-text)' }}>{tier.name}</h3>
                  <div className="mt-3 mb-1">
                    <span className="text-3xl font-extrabold font-mono" style={{ color: 'var(--ept-text)' }}>
                      {tier.price === 0 ? 'Free' : `$${tier.price}`}
                    </span>
                    {tier.price > 0 && <span className="text-sm" style={{ color: 'var(--ept-text-muted)' }}>/mo</span>}
                  </div>
                  <div className="text-xs mb-4" style={{ color: 'var(--ept-text-muted)' }}>{tier.queries.toLocaleString()} queries/month</div>
                  <ul className="space-y-2 mb-6">
                    {tier.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs" style={{ color: 'var(--ept-text-secondary)' }}>
                        <span style={{ color: '#10b981' }}>&#10003;</span> {f}
                      </li>
                    ))}
                  </ul>
                  <Link href="/signup" className="block text-center py-2.5 rounded-lg text-sm font-semibold" style={{
                    backgroundColor: tier.popular ? '#6366f1' : 'transparent',
                    color: tier.popular ? '#fff' : '#818cf8',
                    border: tier.popular ? 'none' : '1px solid #6366f1',
                  }}>
                    {tier.price === 0 ? 'Get Started' : 'Subscribe'}
                  </Link>
                </div>
              ))
            )}
          </div>

          {/* Enterprise CTA */}
          <div className="mt-10 text-center p-8 rounded-2xl mx-auto max-w-3xl" style={{ backgroundColor: 'var(--ept-surface)', border: '1px solid var(--ept-border)' }}>
            <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--ept-text)' }}>Sovereign Plan</h3>
            <p className="text-sm mb-4" style={{ color: 'var(--ept-text-secondary)' }}>
              Unlimited queries. Custom engine development. White-label deployment. On-premise installation. Dedicated account manager.
            </p>
            <a href="mailto:bob@echo-op.com" className="inline-block px-8 py-3 rounded-lg text-sm font-semibold" style={{ backgroundColor: '#f59e0b', color: '#0a0a0f' }}>
              Contact Sales
            </a>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t py-8 text-center" style={{ borderColor: 'var(--ept-border)' }}>
          <p className="text-xs" style={{ color: 'var(--ept-text-muted)' }}>
            Echo Prime Technologies — {totalEngines.toLocaleString()} engines. {totalDoctrines.toLocaleString()} doctrines. AES-256-GCM encrypted. Deterministic audit trails. Court-defensible AI.
          </p>
          <div className="flex justify-center gap-4 mt-3">
            <Link href="/sentinel" className="text-xs underline" style={{ color: '#818cf8' }}>Sentinel</Link>
            <Link href="/pricing" className="text-xs underline" style={{ color: '#818cf8' }}>Pricing</Link>
            <a href="mailto:bob@echo-op.com" className="text-xs underline" style={{ color: '#818cf8' }}>Contact</a>
          </div>
        </div>
      </div>
    </div>
  );
}
