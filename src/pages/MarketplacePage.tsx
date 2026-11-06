import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  SlidersHorizontal, 
  Loader2, 
  Bot, 
  Sparkles,
  ArrowUpDown
} from 'lucide-react';
import { Agent } from '../types';
import { api } from '../services/api';
import { AgentCard } from '../components/marketplace/AgentCard';
import { AgentDetailModal } from '../components/marketplace/AgentDetailModal';

export const MarketplacePage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [sortBy, setSortBy] = useState('rating');
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [agentsRes, catRes] = await Promise.all([
          api.getAgents({
            category: selectedCategory !== 'All' ? selectedCategory : undefined,
            search: search || undefined,
            sort_by: sortBy
          }),
          api.getCategories()
        ]);
        setAgents(agentsRes.agents);
        setCategories(['All', ...catRes]);
      } catch (err: any) {
        setError(err.message || 'Failed to load marketplace agents.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [selectedCategory, search, sortBy]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              AGENT REGISTRY
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {agents.length} Specialized Autonomous Agents
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Specialized Agent Marketplace
          </h1>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl">
            Discover, evaluate, and delegate tasks to verified intelligent agents with deterministic pricing models and capability tags.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5 w-full lg:w-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                selectedCategory === cat
                  ? 'bg-cyan-500 text-navy-950 font-bold shadow-md shadow-cyan-500/20'
                  : 'bg-navy-900 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-800'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search & Sort */}
        <div className="flex items-center gap-3 w-full lg:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search capabilities or name..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-navy-900 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50"
            />
          </div>

          {/* Sort Dropdown */}
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="appearance-none pl-8 pr-8 py-2 rounded-xl bg-navy-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
            >
              <option value="rating">Top Rated</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="completed_tasks">Most Tasks Completed</option>
            </select>
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Agents Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          <span className="text-xs font-mono">Querying registered marketplace agents...</span>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs text-center">
          {error}
        </div>
      ) : agents.length === 0 ? (
        <div className="py-16 text-center text-slate-500 text-sm">
          No specialized agents matched your current filter criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onSelect={(a) => setSelectedAgent(a)}
            />
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <AgentDetailModal
        agent={selectedAgent}
        onClose={() => setSelectedAgent(null)}
      />
    </div>
  );
};
