'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Home,
  Server,
  Cpu,
  HardDrive,
  Activity,
  Play,
  Square,
  RefreshCw,
  Wifi,
  WifiOff,
  Terminal,
  Brain,
  Zap,
  Network,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle,
  Clock,
  Settings,
  Search,
} from 'lucide-react';
import {
  checkSwarmHealth,
  getNodes,
  getClaudeInstances,
  getLLMModels,
  getTrainingJobs,
  launchClaudeOnNode,
  stopClaudeInstance,
  loadModel,
  scanForNodes,
  type SwarmNode,
  type SwarmStatus,
  type ClaudeInstance,
  type LLMModel,
  type TrainingJob,
} from '@/lib/swarm-api';

type TabType = 'nodes' | 'claude' | 'llm' | 'training';

export default function SwarmPage() {
  const [activeTab, setActiveTab] = useState<TabType>('nodes');
  const [status, setStatus] = useState<SwarmStatus | null>(null);
  const [nodes, setNodes] = useState<SwarmNode[]>([]);
  const [claudeInstances, setClaudeInstances] = useState<ClaudeInstance[]>([]);
  const [llmModels, setLLMModels] = useState<LLMModel[]>([]);
  const [trainingJobs, setTrainingJobs] = useState<TrainingJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load all data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [healthData, nodesData, claudeData, modelsData, jobsData] = await Promise.all([
        checkSwarmHealth(),
        getNodes(),
        getClaudeInstances(),
        getLLMModels(),
        getTrainingJobs(),
      ]);

      setStatus(healthData);
      setNodes(nodesData);
      setClaudeInstances(claudeData);
      setLLMModels(modelsData);
      setTrainingJobs(jobsData);
    } catch (err) {
      setError('Failed to connect to Swarm Orchestrator. Make sure it\'s running on localhost:8400');
      console.error('Load error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load and polling
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [loadData]);

  // Handle node scan
  const handleScan = async () => {
    setIsScanning(true);
    try {
      const result = await scanForNodes();
      if (result.success) {
        await loadData();
      }
    } catch (err) {
      console.error('Scan error:', err);
    } finally {
      setIsScanning(false);
    }
  };

  // Handle Claude launch
  const handleLaunchClaude = async (nodeId: string) => {
    try {
      const result = await launchClaudeOnNode(nodeId);
      if (result.success) {
        await loadData();
      } else {
        setError(result.error || 'Failed to launch Claude');
      }
    } catch (err) {
      setError('Failed to launch Claude instance');
    }
  };

  // Handle Claude stop
  const handleStopClaude = async (instanceId: string) => {
    try {
      await stopClaudeInstance(instanceId);
      await loadData();
    } catch (err) {
      setError('Failed to stop Claude instance');
    }
  };

  // Handle model load
  const handleLoadModel = async (modelId: string, nodeId: string) => {
    try {
      const result = await loadModel(modelId, nodeId);
      if (result.success) {
        await loadData();
      } else {
        setError(result.error || 'Failed to load model');
      }
    } catch (err) {
      setError('Failed to load model');
    }
  };

  const getStatusColor = (statusStr: string) => {
    switch (statusStr) {
      case 'online':
      case 'running':
      case 'completed':
      case 'healthy':
        return 'text-green-400';
      case 'offline':
      case 'error':
      case 'failed':
        return 'text-red-400';
      case 'busy':
      case 'pending':
      case 'starting':
        return 'text-yellow-400';
      default:
        return 'text-echo-gray/60';
    }
  };

  const getProgressColor = (percent: number) => {
    if (percent < 50) return 'bg-green-500';
    if (percent < 80) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-echo-magenta/30 bg-echo-black/95 backdrop-blur-md sticky top-0 z-50">
        <nav className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 text-echo-gray/70 hover:text-echo-gray transition-colors">
              <Home className="w-5 h-5" />
            </Link>
            <div className="w-px h-6 bg-echo-magenta/30" />
            <div className="flex items-center gap-2">
              <Network className="w-6 h-6 text-echo-orange" />
              <span className="font-orbitron text-lg font-bold text-echo-orange">
                ECHO SWARM NETWORK
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Status Indicator */}
            <div className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${status?.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'}`} />
              <span className="text-echo-gray/60">
                {status?.status || 'offline'}
              </span>
            </div>

            {/* Quick Stats */}
            {status && status.status === 'healthy' && (
              <div className="hidden md:flex items-center gap-4 text-sm text-echo-gray/60">
                <span className="flex items-center gap-1">
                  <Server className="w-4 h-4" />
                  {status.nodes_online} Nodes
                </span>
                <span className="flex items-center gap-1">
                  <Cpu className="w-4 h-4" />
                  {status.total_gpus} GPUs
                </span>
                <span className="flex items-center gap-1">
                  <Terminal className="w-4 h-4" />
                  {status.claude_instances} Claude
                </span>
              </div>
            )}

            {/* Refresh Button */}
            <button
              onClick={loadData}
              disabled={isLoading}
              className="p-2 rounded-lg border border-echo-magenta/30 text-echo-gray/60 hover:text-echo-magenta hover:border-echo-magenta transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-6">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
              ×
            </button>
          </div>
        )}

        {/* Status Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="glass-panel p-4">
            <div className="flex items-center gap-3">
              <Server className="w-8 h-8 text-echo-magenta" />
              <div>
                <p className="text-2xl font-orbitron font-bold text-echo-orange">
                  {status?.nodes_online || 0}
                </p>
                <p className="text-sm text-echo-gray/60">Nodes Online</p>
              </div>
            </div>
          </div>

          <div className="glass-panel p-4">
            <div className="flex items-center gap-3">
              <Cpu className="w-8 h-8 text-echo-orange" />
              <div>
                <p className="text-2xl font-orbitron font-bold text-echo-orange">
                  {status?.total_gpus || 0}
                </p>
                <p className="text-sm text-echo-gray/60">Total GPUs</p>
              </div>
            </div>
          </div>

          <div className="glass-panel p-4">
            <div className="flex items-center gap-3">
              <HardDrive className="w-8 h-8 text-matrix-magenta" />
              <div>
                <p className="text-2xl font-orbitron font-bold text-echo-orange">
                  {status?.total_vram_gb || 0}GB
                </p>
                <p className="text-sm text-echo-gray/60">Total VRAM</p>
              </div>
            </div>
          </div>

          <div className="glass-panel p-4">
            <div className="flex items-center gap-3">
              <Activity className="w-8 h-8 text-green-400" />
              <div>
                <p className="text-2xl font-orbitron font-bold text-echo-orange">
                  {status?.active_tasks || 0}
                </p>
                <p className="text-sm text-echo-gray/60">Active Tasks</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {[
            { id: 'nodes' as TabType, label: 'Nodes', icon: Server, count: nodes.length },
            { id: 'claude' as TabType, label: 'Claude Instances', icon: Terminal, count: claudeInstances.length },
            { id: 'llm' as TabType, label: 'LLM Models', icon: Brain, count: llmModels.filter(m => m.loaded).length },
            { id: 'training' as TabType, label: 'Training Jobs', icon: Zap, count: trainingJobs.filter(j => j.status === 'running').length },
          ].map(({ id, label, icon: Icon, count }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-rajdhani transition-all whitespace-nowrap ${
                activeTab === id
                  ? 'bg-echo-magenta/20 border border-echo-magenta text-echo-magenta'
                  : 'border border-echo-magenta/30 text-echo-gray/60 hover:text-echo-gray hover:border-echo-magenta/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
              {count > 0 && (
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  activeTab === id ? 'bg-echo-magenta/30' : 'bg-echo-magenta/10'
                }`}>
                  {count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="glass-panel p-6">
          {/* Nodes Tab */}
          {activeTab === 'nodes' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-orbitron text-xl text-echo-magenta">Network Nodes</h2>
                <button
                  onClick={handleScan}
                  disabled={isScanning}
                  className="flex items-center gap-2 px-4 py-2 bg-echo-orange/20 border border-echo-orange rounded-lg hover:bg-echo-orange/30 transition-colors disabled:opacity-50"
                >
                  <Search className={`w-4 h-4 ${isScanning ? 'animate-pulse' : ''}`} />
                  {isScanning ? 'Scanning...' : 'Scan Network'}
                </button>
              </div>

              {nodes.length === 0 ? (
                <div className="text-center py-12 text-echo-gray/60">
                  <WifiOff className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No nodes discovered yet.</p>
                  <p className="text-sm mt-2">Click "Scan Network" to find nodes on your LAN.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {nodes.map((node) => (
                    <div
                      key={node.node_id}
                      className="border border-echo-magenta/30 rounded-lg overflow-hidden"
                    >
                      <div
                        className="p-4 flex items-center justify-between cursor-pointer hover:bg-echo-magenta/5"
                        onClick={() => setExpandedNode(expandedNode === node.node_id ? null : node.node_id)}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`w-3 h-3 rounded-full ${
                            node.status === 'online' ? 'bg-green-400' :
                            node.status === 'busy' ? 'bg-yellow-400' : 'bg-red-400'
                          }`} />
                          <div>
                            <p className="font-orbitron text-echo-orange">{node.hostname}</p>
                            <p className="text-sm text-echo-gray/60">{node.ip_address}:{node.port}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-6">
                          <div className="hidden md:flex items-center gap-4 text-sm text-echo-gray/60">
                            <span>{node.capabilities.gpus} GPU</span>
                            <span>{node.capabilities.gpu_memory_gb}GB VRAM</span>
                            <span>{node.capabilities.cpu_cores} CPU</span>
                          </div>

                          <div className="flex items-center gap-2">
                            {node.capabilities.has_claude_code && (
                              <span className="px-2 py-0.5 text-xs bg-echo-magenta/20 text-echo-magenta rounded">Claude</span>
                            )}
                            {node.capabilities.has_vllm && (
                              <span className="px-2 py-0.5 text-xs bg-echo-orange/20 text-echo-orange rounded">vLLM</span>
                            )}
                          </div>

                          {expandedNode === node.node_id ? (
                            <ChevronUp className="w-5 h-5 text-echo-gray/60" />
                          ) : (
                            <ChevronDown className="w-5 h-5 text-echo-gray/60" />
                          )}
                        </div>
                      </div>

                      {expandedNode === node.node_id && (
                        <div className="px-4 pb-4 border-t border-echo-magenta/20 pt-4">
                          {/* Resource Usage */}
                          <div className="grid grid-cols-3 gap-4 mb-4">
                            <div>
                              <p className="text-sm text-echo-gray/60 mb-1">CPU</p>
                              <div className="h-2 bg-echo-black rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${getProgressColor(node.current_load.cpu_percent)}`}
                                  style={{ width: `${node.current_load.cpu_percent}%` }}
                                />
                              </div>
                              <p className="text-xs text-echo-gray/40 mt-1">{node.current_load.cpu_percent}%</p>
                            </div>
                            <div>
                              <p className="text-sm text-echo-gray/60 mb-1">GPU</p>
                              <div className="h-2 bg-echo-black rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${getProgressColor(node.current_load.gpu_percent)}`}
                                  style={{ width: `${node.current_load.gpu_percent}%` }}
                                />
                              </div>
                              <p className="text-xs text-echo-gray/40 mt-1">{node.current_load.gpu_percent}%</p>
                            </div>
                            <div>
                              <p className="text-sm text-echo-gray/60 mb-1">RAM</p>
                              <div className="h-2 bg-echo-black rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${getProgressColor(node.current_load.memory_percent)}`}
                                  style={{ width: `${node.current_load.memory_percent}%` }}
                                />
                              </div>
                              <p className="text-xs text-echo-gray/40 mt-1">{node.current_load.memory_percent}%</p>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex gap-2">
                            {node.capabilities.has_claude_code && (
                              <button
                                onClick={() => handleLaunchClaude(node.node_id)}
                                className="flex items-center gap-2 px-3 py-2 bg-echo-magenta/20 border border-echo-magenta rounded-lg hover:bg-echo-magenta/30 transition-colors text-sm"
                              >
                                <Play className="w-4 h-4" />
                                Launch Claude
                              </button>
                            )}
                            <button className="flex items-center gap-2 px-3 py-2 border border-echo-magenta/30 rounded-lg hover:border-echo-magenta transition-colors text-sm text-echo-gray/60">
                              <Settings className="w-4 h-4" />
                              Configure
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Claude Instances Tab */}
          {activeTab === 'claude' && (
            <div>
              <h2 className="font-orbitron text-xl text-echo-magenta mb-4">Claude Code Instances</h2>

              {claudeInstances.length === 0 ? (
                <div className="text-center py-12 text-echo-gray/60">
                  <Terminal className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No Claude instances running.</p>
                  <p className="text-sm mt-2">Launch Claude on a node from the Nodes tab.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {claudeInstances.map((instance) => (
                    <div
                      key={instance.instance_id}
                      className="border border-echo-magenta/30 rounded-lg p-4 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-4">
                        <Terminal className={`w-8 h-8 ${getStatusColor(instance.status)}`} />
                        <div>
                          <p className="font-orbitron text-echo-orange">{instance.instance_id.substring(0, 12)}</p>
                          <p className="text-sm text-echo-gray/60">Node: {instance.node_id}</p>
                          {instance.current_task && (
                            <p className="text-sm text-echo-magenta/80 mt-1">Task: {instance.current_task}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="text-right text-sm text-echo-gray/60">
                          <p>{instance.api_calls} API calls</p>
                          <p>{instance.tokens_used.toLocaleString()} tokens</p>
                        </div>

                        <span className={`px-3 py-1 rounded-full text-sm ${
                          instance.status === 'running' ? 'bg-green-500/20 text-green-400' :
                          instance.status === 'idle' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {instance.status}
                        </span>

                        <button
                          onClick={() => handleStopClaude(instance.instance_id)}
                          className="p-2 border border-red-500/30 rounded-lg hover:bg-red-500/10 text-red-400 transition-colors"
                          title="Stop Instance"
                        >
                          <Square className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* LLM Models Tab */}
          {activeTab === 'llm' && (
            <div>
              <h2 className="font-orbitron text-xl text-echo-magenta mb-4">LLM Models</h2>

              {llmModels.length === 0 ? (
                <div className="text-center py-12 text-echo-gray/60">
                  <Brain className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No LLM models available.</p>
                  <p className="text-sm mt-2">Install vLLM on a node to enable model loading.</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {llmModels.map((model) => (
                    <div
                      key={model.model_id}
                      className={`border rounded-lg p-4 ${
                        model.loaded ? 'border-green-500/30 bg-green-500/5' : 'border-echo-magenta/30'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-orbitron text-echo-orange">{model.name}</p>
                          <p className="text-sm text-echo-gray/60">{model.size_gb}GB • {model.vram_required_gb}GB VRAM required</p>
                        </div>
                        {model.loaded ? (
                          <CheckCircle className="w-5 h-5 text-green-400" />
                        ) : (
                          <div className="w-5 h-5 rounded-full border border-echo-magenta/30" />
                        )}
                      </div>

                      <div className="flex flex-wrap gap-2 mb-3">
                        {model.capabilities.map((cap) => (
                          <span key={cap} className="px-2 py-0.5 text-xs bg-echo-magenta/10 text-echo-magenta/80 rounded">
                            {cap}
                          </span>
                        ))}
                      </div>

                      {model.loaded ? (
                        <p className="text-sm text-green-400">Loaded on {model.node_id}</p>
                      ) : (
                        <select
                          onChange={(e) => e.target.value && handleLoadModel(model.model_id, e.target.value)}
                          className="w-full px-3 py-2 bg-echo-black border border-echo-magenta/30 rounded-lg text-echo-gray text-sm"
                          defaultValue=""
                        >
                          <option value="" disabled>Select node to load...</option>
                          {nodes.filter(n => n.status === 'online' && n.capabilities.has_vllm && n.capabilities.gpu_memory_gb >= model.vram_required_gb).map(n => (
                            <option key={n.node_id} value={n.node_id}>
                              {n.hostname} ({n.capabilities.gpu_memory_gb}GB VRAM)
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Training Jobs Tab */}
          {activeTab === 'training' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-orbitron text-xl text-echo-magenta">Training Jobs</h2>
                <button className="flex items-center gap-2 px-4 py-2 bg-echo-orange/20 border border-echo-orange rounded-lg hover:bg-echo-orange/30 transition-colors">
                  <Play className="w-4 h-4" />
                  New Training Job
                </button>
              </div>

              {trainingJobs.length === 0 ? (
                <div className="text-center py-12 text-echo-gray/60">
                  <Zap className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No training jobs.</p>
                  <p className="text-sm mt-2">Create a new training job to fine-tune models.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {trainingJobs.map((job) => (
                    <div
                      key={job.job_id}
                      className="border border-echo-magenta/30 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <p className="font-orbitron text-echo-orange">{job.name}</p>
                          <p className="text-sm text-echo-gray/60">{job.model} • {job.dataset}</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-sm ${
                          job.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                          job.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                          job.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                          'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {job.status}
                        </span>
                      </div>

                      {job.status === 'running' && job.metrics && (
                        <>
                          <div className="mb-2">
                            <div className="flex justify-between text-sm text-echo-gray/60 mb-1">
                              <span>Progress</span>
                              <span>{job.progress}%</span>
                            </div>
                            <div className="h-2 bg-echo-black rounded-full overflow-hidden">
                              <div
                                className="h-full bg-echo-magenta transition-all"
                                style={{ width: `${job.progress}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex gap-4 text-sm text-echo-gray/60">
                            <span>Epoch: {job.metrics.epoch}/{job.metrics.total_epochs}</span>
                            <span>Loss: {job.metrics.loss.toFixed(4)}</span>
                            <span>Accuracy: {(job.metrics.accuracy * 100).toFixed(1)}%</span>
                          </div>
                        </>
                      )}

                      {job.started_at && (
                        <div className="flex items-center gap-2 mt-2 text-sm text-echo-gray/40">
                          <Clock className="w-4 h-4" />
                          Started: {new Date(job.started_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-echo-magenta/30 py-4">
        <div className="container mx-auto px-4 text-center text-echo-gray/50 text-sm">
          ECHO SWARM NETWORK | ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN
        </div>
      </footer>
    </div>
  );
}
