import React from 'react';
import { 
  Shield, 
  ArrowRight, 
  FileText, 
  Activity, 
  Lock, 
  Zap,
  Scale,
  Database,
  ChevronRight
} from 'lucide-react';
import { motion } from 'motion/react';

const SectionLabel = ({ children }) => (
  <div className="flex items-center gap-2 mb-6">
    <div className="w-1 h-1 bg-brand-tan" />
    <span className="text-[10px] uppercase tracking-[0.3em] font-mono text-brand-tan font-medium">
      {children}
    </span>
  </div>
);

const FeatureCard = ({ icon: Icon, title, description }) => (
  <div className="glass-panel p-8 group hover:bg-white/4 transition-all duration-500">
    <div className="w-10 h-10 hairline-border flex items-center justify-center mb-6 text-brand-tan/40 group-hover:text-brand-tan group-hover:border-brand-tan/30 transition-all duration-500">
      <Icon size={20} />
    </div>
    <h3 className="text-lg font-display font-bold mb-3 text-brand-tan">{title}</h3>
    <p className="text-sm text-brand-tan/50 leading-relaxed font-light">
      {description}
    </p>
  </div>
);

export default function LandingPage({ onEnter }) {
  return (
    <div className="min-h-screen bg-brand-matte text-brand-tan/80 overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 w-full z-50 hairline-border-b bg-brand-matte/80 backdrop-blur-md">
        <div className="max-w-350 mx-auto px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-brand-tan flex items-center justify-center">
              <span className="text-brand-matte font-bold text-xs">J</span>
            </div>
            <span className="font-display font-bold tracking-[0.2em] text-brand-tan text-lg">JESSICA.AI</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#system" className="text-[10px] uppercase tracking-widest font-bold text-brand-tan/40 hover:text-brand-tan transition-colors">System</a>
            <a href="#analysis" className="text-[10px] uppercase tracking-widest font-bold text-brand-tan/40 hover:text-brand-tan transition-colors">Analysis</a>
            <a href="#performance" className="text-[10px] uppercase tracking-widest font-bold text-brand-tan/40 hover:text-brand-tan transition-colors">Performance</a>
            <button 
              onClick={onEnter}
              className="bg-brand-tan text-brand-matte px-6 py-2 text-[10px] font-bold uppercase tracking-widest hover:bg-brand-tan-muted transition-all"
            >
              Enter Sandbox
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-32 px-8">
        <div className="max-w-350 mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <SectionLabel>Protocol v4.2.0</SectionLabel>
              <h1 className="text-6xl md:text-8xl font-display font-bold leading-[0.9] mb-8 text-brand-tan">
                High-End <br />
                <span className="text-brand-tan/30 italic">Legal Intelligence</span>
              </h1>
              <p className="text-lg md:text-xl text-brand-tan/60 max-w-xl mb-12 font-light leading-relaxed">
                The definitive AI audit platform for enterprise legal risk. 
                Analyze clauses, evaluate agent performance, and secure your institutional compliance in real-time.
              </p>
              <div className="flex flex-wrap gap-6">
                <button 
                  onClick={onEnter}
                  className="group flex items-center gap-4 bg-brand-tan text-brand-matte px-8 py-4 text-xs font-bold uppercase tracking-[0.2em] hover:bg-brand-tan-muted transition-all"
                >
                  Launch Sandbox
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </button>
                <button className="flex items-center gap-4 hairline-border px-8 py-4 text-xs font-bold uppercase tracking-[0.2em] hover:bg-white/5 transition-all">
                  Documentation
                </button>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.2 }}
              className="relative"
            >
              <div className="aspect-square glass-panel relative overflow-hidden group">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(214,196,176,0.05)_0%,transparent_70%)]" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-64 h-64 hairline-border rounded-full flex items-center justify-center animate-[spin_20s_linear_infinite]">
                    <div className="w-48 h-48 hairline-border rounded-full flex items-center justify-center animate-[spin_15s_linear_infinite_reverse]">
                      <div className="w-32 h-32 bg-brand-tan/5 rounded-full flex items-center justify-center">
                        <Shield size={40} className="text-brand-tan/20" />
                      </div>
                    </div>
                  </div>
                </div>
                {/* Decorative Elements */}
                <div className="absolute top-8 left-8 font-mono text-[8px] text-brand-tan/20 uppercase tracking-[0.3em]">
                  System Status: Active <br />
                  Encryption: AES-256
                </div>
                <div className="absolute bottom-8 right-8 font-mono text-[8px] text-brand-tan/20 uppercase tracking-[0.3em] text-right">
                  Jessica.ai <br />
                  Legal Sandbox v4.2
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 px-8 hairline-border-y bg-white/1">
        <div className="max-w-350 mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-12">
            {[
              { label: "Processing Speed", value: "0.4s", desc: "Per Clause" },
              { label: "Audit Accuracy", value: "99.8%", desc: "Verified" },
              { label: "Risk Detection", value: "12k+", desc: "Daily Audits" },
              { label: "System Uptime", value: "99.99%", desc: "Enterprise" },
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-[10px] uppercase tracking-[0.2em] font-mono text-brand-tan/40 mb-2">{stat.label}</div>
                <div className="text-4xl font-display font-bold text-brand-tan mb-1">{stat.value}</div>
                <div className="text-[9px] uppercase tracking-widest text-brand-tan/20 font-mono">{stat.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="system" className="py-32 px-8">
        <div className="max-w-350 mx-auto">
          <div className="max-w-2xl mb-20">
            <SectionLabel>Core Systems</SectionLabel>
            <h2 className="text-4xl md:text-5xl font-display font-bold mb-6">
              Engineered for <br />
              <span className="text-brand-tan/30 italic">Absolute Precision</span>
            </h2>
            <p className="text-brand-tan/50 font-light leading-relaxed">
              Jessica.ai provides a dual-layered approach to legal intelligence, combining deep document analysis with rigorous agent evaluation.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={FileText}
              title="Risk Review"
              description="Clause-by-clause analysis identifying vulnerabilities, non-compliance, and institutional risks with high-fidelity verdicts."
            />
            <FeatureCard 
              icon={Activity}
              title="Agent Performance"
              description="Real-time monitoring of AI accuracy, reliability scores, and confusion matrix metrics to ensure model integrity."
            />
            <FeatureCard 
              icon={Lock}
              title="Protocol Security"
              description="Enterprise-grade encryption and isolated sandbox environments for sensitive legal data processing."
            />
            <FeatureCard 
              icon={Zap}
              title="Instant Audits"
              description="Rapid processing of complex legal documents with automated grading and compliance scoring."
            />
            <FeatureCard 
              icon={Scale}
              title="Legal Compliance"
              description="Alignment with global regulatory standards and institutional governance frameworks."
            />
            <FeatureCard 
              icon={Database}
              title="Audit History"
              description="Searchable, persistent record of all analysis sessions for long-term tracking and reporting."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-8 bg-brand-tan text-brand-matte">
        <div className="max-w-350 mx-auto text-center">
          <div className="inline-block w-1 h-1 bg-brand-matte mb-8" />
          <h2 className="text-5xl md:text-7xl font-display font-bold mb-12 leading-tight">
            Ready to secure your <br />
            <span className="italic opacity-40">Legal Infrastructure?</span>
          </h2>
          <button 
            onClick={onEnter}
            className="bg-brand-matte text-brand-tan px-12 py-6 text-sm font-bold uppercase tracking-[0.3em] hover:bg-brand-matte/90 transition-all shadow-2xl"
          >
            Enter the Sandbox
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-8 hairline-border-t">
        <div className="max-w-350 mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 bg-brand-tan flex items-center justify-center">
              <span className="text-brand-matte font-bold text-[10px]">J</span>
            </div>
            <span className="font-display font-bold tracking-widest text-brand-tan text-sm">JESSICA.AI</span>
          </div>
          <div className="flex gap-8 text-[10px] font-mono text-brand-tan/30 uppercase tracking-widest">
            <span>© 2026 Protocol Luxury</span>
            <a href="#" className="hover:text-brand-tan transition-colors">Privacy</a>
            <a href="#" className="hover:text-brand-tan transition-colors">Terms</a>
            <a href="#" className="hover:text-brand-tan transition-colors">Security</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
