import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  Shield,
  Search,
  FileText,
  BarChart3,
  ArrowRight,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Database,
  Lock,
  Unlock,
  ChevronRight,
  Download,
  History,
  Scale,
  Clock,
  Filter,
  XCircle,
  TrendingUp,
  Target,
  Zap,
  RefreshCw,
  Loader2,
  Cpu,
  BrainCircuit,
  ShieldAlert,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  AreaChart,
  Area,
  ReferenceLine,
} from 'recharts';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
axios.defaults.baseURL = isLocal ? 'http://127.0.0.1:7860' : '';
// ─── reward constants (mirror backend) ───────────────────────────────────────
const REWARD_MIN   = -100.0;
const REWARD_MAX   =   50.0;
const REWARD_RANGE = REWARD_MAX - REWARD_MIN; // 150

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// ─── helpers ─────────────────────────────────────────────────────────────────
const SectionLabel = ({ children }) => (
  <div className="flex items-center gap-2 mb-4">
    <div className="w-1 h-1 bg-brand-tan" />
    <span className="text-[10px] uppercase tracking-[0.2em] font-mono text-brand-tan font-medium">
      {children}
    </span>
  </div>
);

const MetricCard = ({ title, value, description, icon: Icon, trend }) => (
  <div className="glass-panel p-6 group hover:bg-white/4 transition-all">
    <div className="flex items-center justify-between mb-4">
      <div className="text-[10px] uppercase tracking-[0.2em] font-mono text-brand-tan/40 font-bold">{title}</div>
      <Icon size={16} className="text-brand-tan/40 group-hover:text-brand-tan transition-colors" />
    </div>
    <div className="flex items-end gap-3">
      <div className="text-3xl font-display font-bold text-brand-tan">{value}</div>
      {trend != null && (
        <div className={cn('text-[10px] font-mono mb-1.5', trend > 0 ? 'text-emerald-500' : 'text-red-500')}>
          {trend > 0 ? '+' : ''}{trend}%
        </div>
      )}
    </div>
    <div className="mt-2 text-[10px] font-mono text-brand-tan/20 uppercase tracking-widest">{description}</div>
  </div>
);

// ─── Navbar ──────────────────────────────────────────────────────────────────
const Navbar = ({ activeTab, setActiveTab, onBack, toggleSidebar }) => (
  <nav className="fixed top-0 left-0 w-full z-50 hairline-border-b bg-brand-matte/80 backdrop-blur-md">
    <div className="max-w-400 mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
      <div className="flex items-center gap-4 sm:gap-6">
        <button
          onClick={toggleSidebar}
          className="lg:hidden p-2 -ml-2 text-brand-tan/60 hover:text-brand-tan transition-colors"
        >
          <Filter size={18} />
        </button>
        <button onClick={onBack} className="flex items-center gap-2 group">
          <div className="w-5 h-5 bg-brand-tan flex items-center justify-center group-hover:bg-brand-tan-muted transition-colors">
            <span className="text-brand-matte font-bold text-[10px]">J</span>
          </div>
          <span className="font-display font-bold tracking-widest text-brand-tan text-sm hidden sm:inline">JESSICA.AI</span>
        </button>
        <div className="w-px h-4 bg-brand-border hidden sm:block" />
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('analysis')}
            className={cn(
              'px-2 sm:px-4 py-1.5 text-[9px] sm:text-[10px] uppercase tracking-widest font-bold transition-all whitespace-nowrap',
              activeTab === 'analysis' ? 'text-brand-tan bg-white/5' : 'text-brand-tan/40 hover:text-brand-tan/60'
            )}
          >
            Analysis
          </button>
          <button
            onClick={() => setActiveTab('performance')}
            className={cn(
              'px-2 sm:px-4 py-1.5 text-[9px] sm:text-[10px] uppercase tracking-widest font-bold transition-all whitespace-nowrap',
              activeTab === 'performance' ? 'text-brand-tan bg-white/5' : 'text-brand-tan/40 hover:text-brand-tan/60'
            )}
          >
            Performance
          </button>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-[10px] font-mono tracking-[0.2em] text-brand-tan/40 hidden md:inline">SYSTEM_ACTIVE</span>
        <button className="bg-brand-tan text-brand-matte px-3 sm:px-4 py-1.5 text-[9px] sm:text-[10px] font-bold uppercase tracking-widest hover:bg-brand-tan-muted transition-colors">
          Access
        </button>
      </div>
    </div>
  </nav>
);

const Sidebar = ({ sessions, selectedId, onSelect, isOpen, onClose, loading, onRefresh, onUnlock }) => {
  const [search, setSearch] = useState('');

  // 🚩 STEP 1: Detect which sessions are already unlocked in this browser
  const vaultTokens = useMemo(() => {
    return JSON.parse(localStorage.getItem('vault_tokens') || '{}');
  }, [sessions, loading]); // Re-check when sessions refresh

  const filteredSessions = useMemo(() => {
    return sessions.filter(s =>
      (s.fileName || s.session_id || '').toLowerCase().includes(search.toLowerCase())
    );
  }, [sessions, search]);

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      <aside
        className={cn(
          'w-80 hairline-border-r h-[calc(100vh-3.5rem)] fixed left-0 top-14 bg-brand-matte flex flex-col overflow-hidden z-50 transition-transform duration-300 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="p-6 hairline-border-b">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[10px] uppercase tracking-[0.2em] font-mono text-brand-tan font-bold">Audit Vault</h3>
            <button
              onClick={onRefresh}
              className="p-1 hover:bg-white/5 transition-colors rounded"
            >
              <RefreshCw size={12} className={cn('text-brand-tan/40', loading && 'animate-spin')} />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-tan/30" size={14} />
            <input
              type="text"
              placeholder="Search sessions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white/5 hairline-border rounded-none py-2 pl-9 pr-4 text-xs text-brand-tan placeholder:text-brand-tan/20 focus:outline-none focus:bg-white/10 transition-colors"
            />
          </div>
          <button 
            onClick={onUnlock} 
            className="w-full mt-4 py-2 text-[9px] font-mono uppercase tracking-widest text-brand-tan/40 border border-brand-tan/10 hover:bg-white/5 transition-all flex items-center justify-center gap-2"
          >
            <Lock size={10} /> Unlock Session
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {filteredSessions.length === 0 && !loading && (
            <div className="text-center py-12 text-brand-tan/20 font-mono text-[10px] uppercase tracking-widest">
              Vault is empty
            </div>
          )}
          {filteredSessions.map((session) => {
            const sid = session.session_id || session.id;
            const label = session.fileName || sid?.substring(0, 16).toUpperCase();
            
            // 🚩 STEP 2: Check lock status for this specific item
            const hasKey = !!vaultTokens[sid]; 
            
            const ts = session.timestamp
              ? new Date(session.timestamp * 1000).toLocaleString()
              : session.date || '';

            return (
              <button
                key={sid}
                onClick={() => { onSelect(sid); onClose(); }}
                className={cn(
                  'w-full p-6 text-left hairline-border-b transition-all group relative',
                  selectedId === sid ? 'bg-white/3' : 'hover:bg-white/1'
                )}
              >
                {selectedId === sid && (
                  <div className="absolute left-0 top-0 w-0.5 h-full bg-brand-tan" />
                )}
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-medium text-brand-tan truncate pr-4 font-mono flex items-center gap-2">
                    {/* 🚩 STEP 3: Status Icons */}
                    {hasKey ? (
                      <Unlock size={10} className="text-emerald-500/50" />
                    ) : (
                      <Lock size={10} className="text-brand-tan/20" />
                    )}
                    {label}
                  </div>
                  {session.grade && (
                    <div className="text-[8px] font-mono px-1.5 py-0.5 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                      {session.grade}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[9px] font-mono text-brand-tan/30 uppercase tracking-wider">
                  <Clock size={10} />
                  {ts}
                </div>
              </button>
            );
          })}
        </div>
      </aside>
    </>
  );
};

// ─── Upload Section — real backend call ───────────────────────────────────────
const UploadSection = ({ onUploadSuccess }) => {
  const [file, setFile]           = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading]     = useState(false);
  const [progress, setProgress]   = useState(0);
  const [done, setDone]           = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sessionToken, setSessionToken] = useState(null); // store token directly in state

  const handleDragOver  = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop      = (e) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setDone(false);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post('/audit', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => setProgress(Math.round((e.loaded * 100) / e.total)),
      });

      // 1. Destructure the response
      const { data, session_id, session_token } = res.data;
      
      if (Array.isArray(data)) {
        const synced = data.map((item, i) => ({
          ...item,
          step: i + 1,
          warning: item.warning || 'Audit confirmed compliant by agent.',
        }));
        
        // 2. Persistent Storage (The "History" Fix)
        // This ensures the sidebar can "unlock" this session after a refresh
        const existingTokens = JSON.parse(localStorage.getItem('vault_tokens') || '{}');
        localStorage.setItem('vault_tokens', JSON.stringify({
          ...existingTokens,
          [session_id]: session_token
        }));

        // 3. Update UI State
        onUploadSuccess(synced, session_id, file.name, session_token);
        setSessionId(session_id);
        setSessionToken(session_token); 
        setDone(true);
      } else {
        throw new Error('Audit returned no data.');
      }
      
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Connection lost to backend.';
      alert(`Audit Error: ${msg}`);
    } finally {
      setLoading(false);
      setProgress(0);
    }
};
  if (done) {
  // 🚩 STEP 1: Immediately burn the token into the Vault for future persistence
  // This ensures that even if you don't 'copy' it, the browser remembers it.
  const updateVault = () => {
    const existingTokens = JSON.parse(localStorage.getItem('vault_tokens') || '{}');
    if (sessionId && sessionToken && !existingTokens[sessionId]) {
      localStorage.setItem('vault_tokens', JSON.stringify({
        ...existingTokens,
        [sessionId]: sessionToken
      }));
    }
  };
  updateVault();

  return (
    <div className="mb-8 sm:mb-12">
      <SectionLabel>Audit Protocol Complete</SectionLabel>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 flex flex-col items-center text-center border-emerald-500/10"
      >
        <div className="w-16 h-16 hairline-border flex items-center justify-center mb-4 text-emerald-500 bg-emerald-500/5">
          <Shield size={28} />
        </div>
        
        <h3 className="font-display font-bold text-brand-tan mb-1">Audit Synchronized</h3>
        
        {/* --- ENHANCED SECURE TOKEN BOX --- */}
        <div className="my-6 p-6 bg-black/60 hairline-border w-full max-w-md">
          <div className="flex items-center justify-center gap-2 mb-4">
             <Lock size={12} className="text-brand-tan/40" />
             <p className="text-[10px] font-mono text-brand-tan/40 uppercase tracking-[0.2em]">
               Master Session Key
             </p>
          </div>
          
          <div className="flex flex-col gap-3">
            <code className="text-[11px] font-mono text-emerald-400 bg-white/5 p-4 border border-brand-tan/10 break-all text-left">
              {sessionToken || 'GENERATING_KEY...'} 
            </code>
            
            <button 
              onClick={() => {
                navigator.clipboard.writeText(sessionToken);
                alert("Master Key copied to clipboard. Store this safely!");
              }}
              className="w-full bg-brand-tan text-brand-matte py-2.5 text-[10px] font-bold uppercase tracking-widest hover:bg-brand-tan-muted transition-all"
            >
              Copy Master Key
            </button>
          </div>

          <p className="text-[9px] text-brand-tan/30 mt-4 leading-relaxed italic">
            This key has been added to your local vault. <br/>
            You will need this to access this audit from other devices.
          </p>
        </div>

        <p className="text-[10px] font-mono text-brand-tan/40 mb-8 uppercase tracking-widest">
          Vault Reference: <span className="text-brand-tan">#{sessionId}</span>
        </p>
        
        <button
          onClick={() => { setDone(false); setFile(null); }}
          className="hairline-border px-10 py-3 text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-white/5 transition-all text-brand-tan/60"
        >
          New Inference Trajectory
        </button>
      </motion.div>
    </div>
  );
}
  return (
    <div className="mb-8 sm:mb-12">
      <SectionLabel>Document Ingestion</SectionLabel>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'relative glass-panel p-6 sm:p-12 border-dashed border-2 transition-all duration-500 flex flex-col items-center justify-center text-center group',
          isDragging ? 'border-brand-tan bg-brand-tan/5 scale-[1.01]' : 'border-brand-tan/10 hover:border-brand-tan/30',
          loading && 'pointer-events-none opacity-60'
        )}
      >
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div key="uploading" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center">
              <div className="w-12 h-12 border-2 border-brand-tan/20 border-t-brand-tan rounded-full animate-spin mb-4" />
              <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-brand-tan">
                Processing {progress > 0 ? `${progress}%` : 'Inference Trajectory...'}
              </div>
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
              <div className={cn(
                'w-12 h-12 sm:w-16 sm:h-16 hairline-border flex items-center justify-center mb-4 sm:mb-6 transition-all duration-500',
                file ? 'text-brand-tan border-brand-tan/30' : 'text-brand-tan/20 group-hover:text-brand-tan/40 group-hover:border-brand-tan/30'
              )}>
                {file ? <FileText size={24} /> : <Upload size={20} className="sm:w-6 sm:h-6" />}
              </div>
              <h3 className="text-base sm:text-lg font-display font-bold mb-2 text-brand-tan">
                {file ? file.name : 'Upload Legal Document'}
              </h3>
              <p className="text-[10px] sm:text-xs text-brand-tan/40 mb-6 sm:mb-8 max-w-xs leading-relaxed">
                {file ? 'File loaded — initialize audit below.' : 'Drag and drop PDF, CSV, or TXT for deep protocol analysis. Max 10MB.'}
              </p>
              <div className="flex gap-3 flex-wrap justify-center">
                {!file ? (
                  <label className="bg-brand-tan text-brand-matte px-6 sm:px-8 py-2.5 sm:py-3 text-[9px] sm:text-[10px] font-bold uppercase tracking-[0.2em] cursor-pointer hover:bg-brand-tan-muted transition-all">
                    Select File
                    <input type="file" accept=".pdf,.csv,.txt" className="hidden" onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])} />
                  </label>
                ) : (
                  <>
                    <button
                      onClick={handleUpload}
                      className="flex items-center gap-2 bg-brand-tan text-brand-matte px-8 py-3 text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-brand-tan-muted transition-all"
                    >
                      <Cpu size={14} /> Initialize Audit
                    </button>
                    <button
                      onClick={() => setFile(null)}
                      className="hairline-border px-6 py-3 text-[10px] font-bold uppercase tracking-widest hover:bg-white/5 transition-all text-brand-tan/40"
                    >
                      Clear
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

// ─── Analysis Tab ─────────────────────────────────────────────────────────────
const DocumentAnalysisTab = ({ auditData, metrics, onUpload, sessionId }) => {
  
  const handleExportPDF = async () => {
    const sid = sessionId || auditData[0]?.session_id;
    if (!sid) return alert('No Session ID available.');
    
    // --- UPDATED: Retrieve the specific token from the Token Map ---
    const vaultTokens = JSON.parse(localStorage.getItem('vault_tokens') || '{}');
    const token = vaultTokens[sid]; 

    if (!token) {
      return alert('Security token missing for this session. Please use the Unlock feature in the Sidebar.');
    }

    try {
      // Fetch the PDF as a BLOB with the specific session token
      const response = await axios.get(`/export/report/${sid}`, {
        headers: { 
          'X-Session-Token': token 
        },
        responseType: 'blob', 
      });

      // Create a temporary URL for the binary data
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(pdfBlob);
      
      // Trigger the download
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Legal_Audit_Report_${sid}.pdf`);
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      console.error('PDF Export Error:', err);
      const errorMsg = err.response?.data?.detail || 'Unauthorized access to PDF';
      alert(`Export Error: ${errorMsg}`);
    }
  };


  const handleExportJSON = () => {
  // 1. Create a sanitized copy of the data
  // We use .map() to create a new list and remove the session_token
  const sanitizedData = auditData.map(({ session_token, ...rest }) => rest);

  // 2. Use the sanitized data for the export
  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(sanitizedData, null, 2));
  
  const a = document.createElement('a');
  a.href = dataStr;
  a.download = `audit_${sessionId || 'session'}.json`;
  a.click();
};

  const riskItems = auditData.filter(i => i.action === 1);
  const hasData   = auditData.length > 0;

  return (
    <div className="space-y-6 sm:space-y-8">
      <UploadSection onUploadSuccess={onUpload} />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* --- UPDATED HEADER SECTION --- */}
        <div className="flex items-center gap-3">
          <SectionLabel>Analysis Overview</SectionLabel>
          
          {sessionId && (
            <div className="flex items-center gap-2 bg-white/5 hairline-border px-2 py-1 rounded-sm transition-all hover:bg-white/10">
              <Lock size={10} className="text-brand-tan/40" />
              <span className="text-[8px] font-mono text-brand-tan/60 uppercase tracking-tighter">
                Session: <span className="text-brand-tan font-bold">{sessionId.substring(0, 12)}...</span>
              </span>
            </div>
          )}
        </div>
        {/* ------------------------------ */}

        {hasData && (
          <div className="flex gap-2 sm:gap-3">
            <button
              onClick={handleExportJSON}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 text-[9px] sm:text-[10px] uppercase tracking-widest font-bold text-brand-tan/60 border border-brand-tan/10 px-3 sm:px-4 py-2 hover:bg-white/5 transition-all"
            >
              <FileText size={12} /> JSON
            </button>
            <button
              onClick={handleExportPDF}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 text-[9px] sm:text-[10px] uppercase tracking-widest font-bold text-brand-tan border border-brand-tan/20 px-3 sm:px-4 py-2 hover:bg-white/5 transition-all"
            >
              <Download size={12} /> Export Report
            </button>
          </div>
        )}
      </div>

      {!hasData ? (
        <div className="glass-panel py-24 flex flex-col items-center justify-center text-center">
          <History size={32} className="text-brand-tan/10 mb-4" />
          <p className="text-[10px] font-mono uppercase tracking-[0.3em] text-brand-tan/20">
            Awaiting Trajectory Feed...
          </p>
          <p className="text-[9px] font-mono text-brand-tan/10 mt-2 uppercase tracking-widest">
            Upload a file or select a vault session
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            <MetricCard title="Agent Risk Flags" value={metrics.risks} description="Identified vulnerabilities" icon={ShieldAlert} />
            <MetricCard title="Reliability Grade" value={metrics.grade} description="Normalized RL score" icon={Scale} />
            <div className="glass-panel p-6 group hover:bg-white/4 transition-all flex flex-col items-center justify-center">
              <p className="text-[10px] uppercase tracking-[0.2em] font-mono text-brand-tan/40 font-bold mb-2">Oracle Consensus</p>
              <p className={cn('text-5xl font-display font-bold', metrics.consensus > 70 ? 'text-emerald-400' : 'text-amber-400')}>
                {metrics.consensus}%
              </p>
            </div>
          </div>

          {/* Agent Final Inference Banner */}
          <div className="glass-panel p-6 flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <BrainCircuit size={12} className="text-brand-tan/40" />
                <span className="text-[10px] font-mono uppercase tracking-widest text-brand-tan/40">Agent Final Inference</span>
              </div>
              <p className="text-xs text-brand-tan/60 leading-relaxed italic">"{metrics.summary}"</p>
            </div>
          </div>

          {/* Audit Cards */}
          <div className="space-y-4">
            <SectionLabel>Clause-by-Clause Results</SectionLabel>
            <div className="space-y-3 max-h-150 overflow-y-auto pr-2 custom-scrollbar">
              {auditData.map((item, i) => {
                const isFlag    = item.action === 1;
                const isOracle  = Boolean(item.is_actually_risk);
                const isSync    = isFlag === isOracle;
                return (
                  <div
                    key={`${item.session_id}-${i}`}
                    className={cn(
                      'p-6 hairline-border transition-all',
                      isFlag ? 'bg-red-500/5 border-red-500/10' : 'bg-white/1'
                    )}
                  >
                    <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
                      <div className="flex gap-2 items-center flex-wrap">
                        <span className={cn(
                          'text-[9px] font-mono font-bold uppercase tracking-widest px-3 py-1',
                          isFlag ? 'bg-red-500/20 text-red-400 border border-red-500/20' : 'bg-white/5 text-brand-tan/40 hairline-border'
                        )}>
                          {isFlag ? '⚑ AGENT: RISK' : 'AGENT: SAFE'}
                        </span>
                        <span className={cn(
                          'text-[8px] font-mono uppercase tracking-widest px-2 py-0.5 border border-dashed flex items-center gap-1',
                          isSync ? 'border-emerald-500/30 text-emerald-500' : 'border-amber-500/30 text-amber-500'
                        )}>
                          <Zap size={8} />
                          Oracle: {isOracle ? 'RISK' : 'SAFE'}
                        </span>
                      </div>
                      <span className="text-[9px] font-mono text-brand-tan/20">
                        REW {parseFloat(item.reward) > 0 ? '+' : ''}{parseFloat(item.reward).toFixed(1)}
                      </span>
                    </div>
                    <p className="text-xs text-brand-tan/60 italic leading-relaxed mb-3">"{item.text}"</p>
                    {item.warning && (
                      <div className="bg-white/2 hairline-border p-4">
                        <p className="text-[9px] font-mono uppercase tracking-widest text-brand-tan/40 mb-2 flex items-center gap-1">
                          <BrainCircuit size={10} /> Agent Rationale
                        </p>
                        <p className="text-[11px] text-brand-tan/60 leading-relaxed">{item.warning}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ─── Performance Tab ──────────────────────────────────────────────────────────
const PerformanceTab = ({ auditData, metrics, sessionId }) => {
  
  // FIX: Secure PDF Export using Token Map and Axios Blob
  const handleExportPDF = async () => {
    const sid = sessionId || auditData[0]?.session_id;
    if (!sid) return alert('No Session ID available.');
    
    // 1. Retrieve the specific token for THIS session from the Token Map
    const vaultTokens = JSON.parse(localStorage.getItem('vault_tokens') || '{}');
    const token = vaultTokens[sid];

    if (!token) {
      return alert('Security token missing for this session. Please use the Unlock feature in the Sidebar.');
    }

    try {
      // 2. Use axios to send the specific token header and receive binary data
      const response = await axios.get(`/export/${sid}`, {
        headers: { 
          'X-Session-Token': token 
        },
        responseType: 'blob', // Mandatory for PDFs
      });

      // 3. Trigger the binary download
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(pdfBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Agent_Performance_Report_${sid}.pdf`);
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      console.error('PDF Export Error:', err);
      const errorMsg = err.response?.data?.detail || 'Unauthorized access to PDF';
      alert(`Export Error: ${errorMsg}`);
    }
  };

  const handleExportJSON = () => {
    // Create a copy of the data without the session_token for security
    const sanitizedData = auditData.map(({ session_token, ...rest }) => rest);
    
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(sanitizedData, null, 2));
    const a = document.createElement('a');
    a.href = dataStr;
    a.download = `performance_${sessionId || 'session'}.json`;
    a.click();
  };

  const hasData = auditData.length > 0;

  // ... (keep the useMemo logic exactly as it is) ...
  const { tp, fp, fn, tn, trajectory, totalReward, reliability, accuracy } = useMemo(() => {
    if (!hasData) return { tp: 0, fp: 0, fn: 0, tn: 0, trajectory: [], totalReward: 0, reliability: '0.000', accuracy: '0.000' };

    const tp = auditData.filter(i => i.action === 1 &&  i.is_actually_risk).length;
    const fp = auditData.filter(i => i.action === 1 && !i.is_actually_risk).length;
    const fn = auditData.filter(i => i.action === 0 &&  i.is_actually_risk).length;
    const tn = auditData.filter(i => i.action === 0 && !i.is_actually_risk).length;

    let cum = 0;
    const trajectory = [
      { step: 0, cumulative: 0 },
      ...auditData.map((item, idx) => {
        cum += parseFloat(item.reward) || 0;
        return { step: idx + 1, cumulative: parseFloat(cum.toFixed(4)) };
      }),
    ];

    const total       = auditData.length;
    const avgReward   = cum / total;
    const normalized  = Math.max(0, Math.min(1, (avgReward - REWARD_MIN) / REWARD_RANGE));
    const accuracy    = ((tp + tn) / total * 100).toFixed(1);

    return { tp, fp, fn, tn, trajectory, totalReward: cum.toFixed(3), reliability: normalized.toFixed(3), accuracy };
  }, [auditData, hasData]);

  const matrixItems = [
    { name: 'True Positive',  value: tp, color: '#34d399' },
    { name: 'False Positive', value: fp, color: '#f87171' },
    { name: 'False Negative', value: fn, color: '#fbbf24' },
    { name: 'True Negative',  value: tn, color: '#60a5fa' },
  ];
  const matrixTotal = tp + fp + fn + tn || 1;

  return (
    <div className="space-y-6 sm:space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* --- UPDATED HEADER SECTION --- */}
        <div className="flex items-center gap-3">
          <SectionLabel>Agent Evaluation</SectionLabel>
          
          {sessionId && (
            <div className="flex items-center gap-2 bg-white/5 hairline-border px-2 py-1 rounded-sm transition-all hover:bg-white/10">
              <Lock size={10} className="text-brand-tan/40" />
              <span className="text-[8px] font-mono text-brand-tan/60 uppercase tracking-tighter">
                Session: <span className="text-brand-tan font-bold">{sessionId.substring(0, 12)}...</span>
              </span>
            </div>
          )}
        </div>
        {/* ------------------------------ */}

        {hasData && (
          <div className="flex gap-2 sm:gap-3">
            <button
              onClick={handleExportJSON}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 text-[9px] sm:text-[10px] uppercase tracking-widest font-bold text-brand-tan/60 border border-brand-tan/10 px-3 sm:px-4 py-2 hover:bg-white/5 transition-all"
            >
              <FileText size={12} /> JSON
            </button>
            <button
              onClick={handleExportPDF}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 text-[9px] sm:text-[10px] uppercase tracking-widest font-bold text-brand-tan border border-brand-tan/20 px-3 sm:px-4 py-2 hover:bg-white/5 transition-all"
            >
              <Download size={12} /> Export Agent Report
            </button>
          </div>
        )}
      </div>

      {!hasData ? (
        <div className="glass-panel py-24 flex flex-col items-center text-center">
          <Activity size={32} className="text-brand-tan/10 mb-4 animate-pulse" />
          <p className="text-[10px] font-mono uppercase tracking-[0.3em] text-brand-tan/20">
            Awaiting Trajectory Feed...
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <MetricCard title="True Positives"  value={tp} description="Verified risk counts"  icon={CheckCircle2} />
            <MetricCard title="False Positives" value={fp} description="Hallucination counts"  icon={XCircle} />
            <MetricCard title="False Negatives" value={fn} description="Critical miss counts"  icon={AlertTriangle} />
            <MetricCard title="True Negatives"  value={tn} description="Correct clear counts"  icon={Shield} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
            <MetricCard title="RL Reward"    value={totalReward}         description="Total accrued"     icon={Zap} />
            <MetricCard title="Reliability"  value={reliability}         description="Normalized index"  icon={Target} />
            <MetricCard title="Accuracy"     value={`${accuracy}%`}      description="Oracle sync"       icon={TrendingUp} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-6 sm:gap-8">
            {/* Reward Convergence Chart */}
            <div className="glass-panel p-6 sm:p-8">
              <div className="flex items-center gap-2 mb-8">
                <Activity size={14} className="text-brand-tan/40" />
                <h3 className="text-base sm:text-lg font-bold">Reward Convergence Trajectory</h3>
              </div>
              <div className="h-64 sm:h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trajectory}>
                    <defs>
                      <linearGradient id="rlGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#D6C4B0" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#D6C4B0" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                    <XAxis dataKey="step" hide />
                    <YAxis stroke="rgba(214,196,176,0.2)" fontSize={10} domain={['auto', 'auto']} tick={{ fill: 'rgba(214,196,176,0.4)' }} />
                    <ReferenceLine y={0} stroke="rgba(214,196,176,0.2)" strokeDasharray="3 3" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0A0A0A', border: '1px solid rgba(214,196,176,0.15)', fontSize: '10px', fontFamily: 'monospace' }}
                      itemStyle={{ color: '#D6C4B0' }}
                    />
                    <Area type="monotone" dataKey="cumulative" stroke="#D6C4B0" strokeWidth={2} fill="url(#rlGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Confusion Matrix */}
            <div className="glass-panel p-6 sm:p-8">
              <h3 className="text-base sm:text-lg font-bold mb-8">Confusion Matrix</h3>
              <div className="space-y-6">
                {matrixItems.map((item, i) => (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[9px] sm:text-[10px] font-mono text-brand-tan/40 uppercase tracking-widest">{item.name}</span>
                      <span className="text-xs font-bold text-brand-tan">{item.value}</span>
                    </div>
                    <div className="h-1.5 bg-white/5 w-full rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(item.value / matrixTotal) * 100}%` }}
                        className="h-full"
                        style={{ backgroundColor: item.color }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-8 pt-6 border-t border-brand-border">
                <div className="text-[10px] font-mono text-brand-tan/40 mb-4 uppercase tracking-widest">Model Status</div>
                <div className="flex items-center gap-2 text-emerald-500 text-xs font-bold">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  {parseFloat(reliability) > 0.7 ? 'HIGH_RELIABILITY_ACTIVE' : 'REVIEW_REQUIRED'}
                </div>
              </div>
            </div>
          </div>

          {/* Inference Trajectory Log */}
          <div className="glass-panel p-6 sm:p-8">
            <SectionLabel>Inference Trajectory Log</SectionLabel>
            <div className="max-h-64 overflow-y-auto custom-scrollbar space-y-2">
              {[...auditData].reverse().map((item, i) => {
                const isMatch = item.action === (item.is_actually_risk ? 1 : 0);
                const rew     = parseFloat(item.reward) || 0;
                return (
                  <div
                    key={i}
                    className={cn(
                      'flex items-center justify-between p-3 hairline-border transition-all',
                      isMatch ? 'bg-white/1' : 'bg-amber-500/5 border-amber-500/10'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn('w-1.5 h-1.5 rounded-full', isMatch ? 'bg-brand-tan/40' : 'bg-amber-500 animate-pulse')} />
                      <span className="text-[9px] font-mono text-brand-tan/40">#{String(auditData.length - i).padStart(3, '0')}</span>
                    </div>
                    <div className="text-right">
                      <span className={cn('text-[9px] font-mono font-bold uppercase block', item.action === 1 ? 'text-red-400' : 'text-brand-tan/40')}>
                        {item.action === 1 ? 'FLAGGED' : 'CLEARED'}
                      </span>
                      <span className="text-[7px] font-mono text-brand-tan/20 block">
                        REW: {rew > 0 ? '+' : ''}{rew}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard({ onBack }) {
  const [activeTab,    setActiveTab]    = useState('analysis');
  const [auditData,    setAuditData]    = useState([]);
  const [sessionId,    setSessionId]    = useState(localStorage.getItem('last_viewed_session') || null);
  const [vaultSessions, setVaultSessions] = useState([]);
  const [selectedVaultId, setSelectedVaultId] = useState(null);
  const [vaultLoading, setVaultLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [sessionStats, setSessionStats] = useState({});
  const [isUnlockOpen, setIsUnlockOpen] = useState(false);
  const [unlockForm, setUnlockForm] = useState({ id: '', token: '' });

  // Fetch vault session list from backend
 const [sessionTokens, setSessionTokens] = useState(() => 
    JSON.parse(localStorage.getItem('vault_tokens') || '{}')
  );
  // Helper to save tokens to localStorage
  const saveToken = (id, token) => {
    // Always read from localStorage directly to avoid stale state spread
    const existing = JSON.parse(localStorage.getItem('vault_tokens') || '{}');
    const updatedTokens = { ...existing, [id]: token };
    setSessionTokens(updatedTokens);
    localStorage.setItem('vault_tokens', JSON.stringify(updatedTokens));
  };
  // ── Local vault helpers (localStorage fallback when ADMIN_TOKEN not set) ─────
  const readLocalVault = () => {
    try { return JSON.parse(localStorage.getItem('local_vault') || '[]'); }
    catch { return []; }
  };
  const writeLocalVault = (sessions) => {
    localStorage.setItem('local_vault', JSON.stringify(sessions));
  };
  const addToLocalVault = (session) => {
    const existing = readLocalVault();
    const merged = [session, ...existing.filter(s => s.session_id !== session.session_id)];
    writeLocalVault(merged);
  };
  const ADMIN_KEY = "dev_secret_zoro";
  const fetchVault = async () => {
    setVaultLoading(true);
    try {
      const res = await axios.get('/developer/sessions',
        {
          headers: { 'x-admin-token': ADMIN_KEY }
        }
      );
      const sessions = res.data.sessions;
      if (Array.isArray(sessions)) {
        setVaultSessions(sessions);
        localStorage.setItem('local_vault', JSON.stringify(sessions));
      }
    } catch (err) {
      console.error('Vault fetch error:', err);
      // Fallback to local storage if server is unreachable
      const local = JSON.parse(localStorage.getItem('local_vault') || '[]');
      setVaultSessions(local);
    } finally {
      setVaultLoading(false);
    }
  };

  useEffect(() => { fetchVault();
    const lastId = localStorage.getItem('last_viewed_session');
    if (lastId) {
      handleVaultSelect(lastId, true);
    }
   }, []);

  // Load a session from the vault
  const handleVaultSelect = async (sid, isAutoRestore = false) => {
  if (!sid) return;
  
  // 1. Update UI state immediately for responsiveness
  setSelectedVaultId(sid);
  
  localStorage.setItem('last_viewed_session', sid);
  // ------------------------------

  console.log("Attempting to load session:", sid);

  // 2. Get the token SPECIFIC to this session ID — read from localStorage directly
  //    to avoid stale closure when this runs on page-load via useEffect
  const token = JSON.parse(localStorage.getItem('vault_tokens') || '{}')[sid];

  // 3. Security gate: if no token is stored for this session, demand one before
  //    making any API call. Sending undefined lets the backend legacy-mode bypass it.
  if (!token && !isAutoRestore) {
    setIsUnlockOpen(true);
    setUnlockForm({ id: sid, token: '' });
    return;
  }

  try {
    
    const [statsRes, dataRes] = await Promise.all([
      axios.get(`/stats/${sid}`, {
        headers: { 'X-Session-Token': token }
      }),
      axios.get(`/data/${sid}`, {
        headers: { 'X-Session-Token': token }
      })
    ]);

    // 3. Update Summary Stats
    if (typeof setSessionStats === 'function') {
      setSessionStats(statsRes.data);
    }

    // 4. Update Full Audit Data
    setAuditData(Array.isArray(dataRes.data) ? dataRes.data : []);
    setSessionId(sid);
    
  } catch (err) {
    console.error('Vault Access Error:', err);
    
    // On auto-restore (page load), silently clear stale session instead of showing errors
    if (isAutoRestore) {
      if (err.response?.status === 404) {
        // Session no longer exists on server (e.g. Space restarted) — clear stale localStorage
        localStorage.removeItem('last_viewed_session');
      } else if (err.response?.status === 403) {
        // Token is stale — open unlock modal so user can re-enter it
        setIsUnlockOpen(true);
        setUnlockForm({ id: sid, token: '' });
      }
      return;
    }

    // Manual selection — show errors normally
    if (err.response?.status === 403) {
      setIsUnlockOpen(true);
      setUnlockForm({ id: sid, token: '' });
    } else {
      const errorMsg = err.response?.data?.detail || err.message || 'Unauthorized access';
      alert(`Failed to load session: ${errorMsg}`);
    }
  }
};
const handleManualUnlock = async () => {
  const { id, token } = unlockForm;
  if (!id || !token) return alert("Please provide both Session ID and Token");

  try {
    // 1. Verify the token works with the server
    await axios.get(`/stats/${id}`, {
      headers: { 'X-Session-Token': token }
    });

    // 2. FIX: Save this token to our map so we never have to unlock it again
    saveToken(id, token);
    
    // 3. Update UI state
    setSessionId(id);
    setSelectedVaultId(id);
    
    // 4. Load the data using the now-saved token
    await handleVaultSelect(id); 
    
    setIsUnlockOpen(false);
    setUnlockForm({ id: '', token: '' });
  } catch (err) {
    const msg = err.response?.data?.detail || "Invalid ID or Token";
    alert(`Access Denied: ${msg}`);
  }
};
  // Handle fresh upload result
  const handleUploadSuccess = (data, sid, fileName, token) => {
    setAuditData(data);
    setSessionId(sid);
    setSelectedVaultId(sid);
    saveToken(sid, token);
    // Add to local vault so history survives refresh even without ADMIN_TOKEN
    const newEntry = { session_id: sid, fileName, timestamp: Date.now() / 1000 };
    addToLocalVault(newEntry);
    setVaultSessions(prev => [newEntry, ...prev.filter(s => s.session_id !== sid)]);
    fetchVault(); // re-sync with server if ADMIN_TOKEN is available
  };
useEffect(() => { 
    // Restore the last active session from localStorage on mount
    const lastId = localStorage.getItem('last_viewed_session');
    if (lastId) {
      handleVaultSelect(lastId, true); // isAutoRestore=true — suppress unlock modal on 404
    }
  }, []); 
  // Compute derived metrics
  const metrics = useMemo(() => {
    const total = auditData.length;
    if (total === 0) return { risks: 0, grade: '0.000', summary: 'Initialize System Protocol...', consensus: 0 };

    const risks     = auditData.filter(i => i.action === 1).length;
    const matches   = auditData.filter(i => (i.action === 1) === Boolean(i.is_actually_risk)).length;
    const consensus = Math.round((matches / total) * 100);

    const totalReward = auditData.reduce((acc, curr) => acc + (parseFloat(curr.reward) || 0), 0);
    const avgReward   = totalReward / total;
    const normalized  = Math.max(0, Math.min(1, (avgReward - REWARD_MIN) / REWARD_RANGE));

    const summary = consensus > 80
      ? `Audit synchronized. Agent matched Oracle truth in ${consensus}% of segments.`
      : `Discrepancy detected. Low Oracle consensus (${consensus}%). Technical review required.`;

    return { risks, grade: normalized.toFixed(3), summary, consensus };
  }, [auditData]);

  // Sidebar data — merge vault sessions with any local state shape
  const sidebarSessions = useMemo(() =>
    vaultSessions.map(s => ({
      ...s,
      id: s.session_id,
      fileName: s.fileName || s.session_id?.substring(0, 16).toUpperCase(),
    })), [vaultSessions]);

  return (
    <div className="min-h-screen bg-brand-matte selection:bg-brand-tan/30 text-brand-tan/80">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onBack={onBack}
        toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      <div className="flex pt-14">
        <Sidebar
          sessions={sidebarSessions}
          selectedId={selectedVaultId}
          onSelect={handleVaultSelect}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          loading={vaultLoading}
          onRefresh={fetchVault}
          onUnlock={() => { setIsUnlockOpen(true); setUnlockForm({ id: '', token: '' }); }}
        />

        <main className="flex-1 lg:ml-80 p-4 sm:p-6 lg:p-10 max-w-300 mx-auto w-full">
          <AnimatePresence mode="wait">
            <motion.div
              key={`${activeTab}-${sessionId}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === 'analysis' ? (
                <DocumentAnalysisTab
                  auditData={auditData}
                  metrics={metrics}
                  onUpload={handleUploadSuccess}
                  sessionId={sessionId}
                />
              ) : (
                <PerformanceTab
                  auditData={auditData}
                  metrics={metrics}
                  sessionId={sessionId}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
          <AnimatePresence>
            {isUnlockOpen && (
            <div className="fixed inset-0 z-100 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }} 
              animate={{ scale: 1, opacity: 1 }} 
              exit={{ scale: 0.9, opacity: 0 }}
              className="glass-panel p-8 w-full max-w-sm border-brand-tan/20"
            >
              <h3 className="text-brand-tan font-display font-bold mb-4 uppercase tracking-widest text-center">Session Unlock</h3>
              <div className="space-y-4">
                <input 
                  type="text" placeholder="Session ID" 
                  className="w-full bg-white/5 hairline-border p-2 text-xs text-brand-tan focus:outline-none"
                  value={unlockForm.id} onChange={e => setUnlockForm({...unlockForm, id: e.target.value})}
                />
                <input 
                  type="password" placeholder="Session Token" 
                  className="w-full bg-white/5 hairline-border p-2 text-xs text-brand-tan focus:outline-none"
                  value={unlockForm.token} onChange={e => setUnlockForm({...unlockForm, token: e.target.value})}
                />
                <div className="flex gap-2 mt-6">
                  <button onClick={() => setIsUnlockOpen(false)} className="flex-1 py-2 text-[10px] uppercase font-bold text-brand-tan/40">Cancel</button>
                  <button onClick={handleManualUnlock} className="flex-1 py-2 bg-brand-tan text-brand-matte text-[10px] uppercase font-bold">Unlock</button>
                </div>
              </div>
            </motion.div>
            </div>
            )}
          </AnimatePresence>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(214, 196, 176, 0.1); }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(214, 196, 176, 0.2); }
        .hairline-border-y { border-top: 1px solid rgba(214,196,176,0.15); border-bottom: 1px solid rgba(214,196,176,0.15); }
        @media print {
          nav, aside, button { display: none !important; }
          main { margin-left: 0 !important; padding: 0 !important; }
          .glass-panel { border: 1px solid #000 !important; background: #fff !important; color: #000 !important; }
          * { color: #000 !important; }
        }
      `}</style>
    </div>
  );
}