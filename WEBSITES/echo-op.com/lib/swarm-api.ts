/**
 * Echo Swarm Network API Client
 * Connects to the Swarm Orchestrator running locally or via remote
 */

// Default to local orchestrator, can be configured
const SWARM_API_BASE = process.env.NEXT_PUBLIC_SWARM_API || 'http://localhost:8400';

export interface SwarmNode {
  node_id: string;
  hostname: string;
  ip_address: string;
  port: number;
  status: 'online' | 'offline' | 'busy' | 'error';
  capabilities: {
    gpus: number;
    gpu_memory_gb: number;
    cpu_cores: number;
    ram_gb: number;
    has_claude_code: boolean;
    has_vllm: boolean;
  };
  current_load: {
    cpu_percent: number;
    gpu_percent: number;
    memory_percent: number;
  };
  last_heartbeat: string;
  tasks_running: number;
}

export interface ClaudeInstance {
  instance_id: string;
  node_id: string;
  status: 'running' | 'idle' | 'error' | 'starting';
  session_id?: string;
  current_task?: string;
  started_at: string;
  api_calls: number;
  tokens_used: number;
}

export interface LLMModel {
  model_id: string;
  name: string;
  size_gb: number;
  loaded: boolean;
  node_id?: string;
  vram_required_gb: number;
  capabilities: string[];
}

export interface TrainingJob {
  job_id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  model: string;
  dataset: string;
  progress: number;
  started_at?: string;
  estimated_completion?: string;
  nodes_assigned: string[];
  metrics?: {
    loss: number;
    accuracy: number;
    epoch: number;
    total_epochs: number;
  };
}

export interface SwarmStatus {
  status: string;
  nodes_online: number;
  total_gpus: number;
  total_vram_gb: number;
  active_tasks: number;
  claude_instances: number;
  uptime_seconds: number;
}

// Check swarm orchestrator health
export async function checkSwarmHealth(): Promise<SwarmStatus> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/stats`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Swarm API error: ${response.status}`);
    }

    const data = await response.json();
    return {
      status: 'healthy',
      nodes_online: data.nodes_online || 0,
      total_gpus: data.total_gpus || 0,
      total_vram_gb: data.total_vram_gb || 0,
      active_tasks: data.active_tasks || 0,
      claude_instances: data.claude_instances || 0,
      uptime_seconds: data.uptime_seconds || 0,
    };
  } catch (error) {
    console.error('Swarm health check failed:', error);
    return {
      status: 'offline',
      nodes_online: 0,
      total_gpus: 0,
      total_vram_gb: 0,
      active_tasks: 0,
      claude_instances: 0,
      uptime_seconds: 0,
    };
  }
}

// Get all discovered nodes
export async function getNodes(): Promise<SwarmNode[]> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/nodes`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Failed to get nodes: ${response.status}`);
    }

    const data = await response.json();
    return data.nodes || [];
  } catch (error) {
    console.error('Failed to get nodes:', error);
    return [];
  }
}

// Get Claude Code instances
export async function getClaudeInstances(): Promise<ClaudeInstance[]> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/claude/instances`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Failed to get Claude instances: ${response.status}`);
    }

    const data = await response.json();
    return data.instances || [];
  } catch (error) {
    console.error('Failed to get Claude instances:', error);
    return [];
  }
}

// Launch Claude Code on a node
export async function launchClaudeOnNode(nodeId: string, task?: string): Promise<{ success: boolean; instance_id?: string; error?: string }> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/claude/start/${nodeId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task }),
    });

    return await response.json();
  } catch (error) {
    console.error('Failed to launch Claude:', error);
    return { success: false, error: String(error) };
  }
}

// Stop Claude instance
export async function stopClaudeInstance(instanceId: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/claude/stop/${instanceId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    return await response.json();
  } catch (error) {
    console.error('Failed to stop Claude instance:', error);
    return { success: false };
  }
}

// Get available LLM models
export async function getLLMModels(): Promise<LLMModel[]> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/models`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Failed to get models: ${response.status}`);
    }

    const data = await response.json();
    return data.models || [];
  } catch (error) {
    console.error('Failed to get LLM models:', error);
    return [];
  }
}

// Load a model on a node
export async function loadModel(modelId: string, nodeId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/models/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId, node_id: nodeId }),
    });

    return await response.json();
  } catch (error) {
    console.error('Failed to load model:', error);
    return { success: false, error: String(error) };
  }
}

// Get training jobs
export async function getTrainingJobs(): Promise<TrainingJob[]> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/training/jobs`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Failed to get training jobs: ${response.status}`);
    }

    const data = await response.json();
    return data.jobs || [];
  } catch (error) {
    console.error('Failed to get training jobs:', error);
    return [];
  }
}

// Start a training job
export async function startTrainingJob(config: {
  name: string;
  model: string;
  dataset: string;
  epochs: number;
  batch_size: number;
}): Promise<{ success: boolean; job_id?: string; error?: string }> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/training/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    return await response.json();
  } catch (error) {
    console.error('Failed to start training job:', error);
    return { success: false, error: String(error) };
  }
}

// Cancel a training job
export async function cancelTrainingJob(jobId: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/training/stop/${jobId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    return await response.json();
  } catch (error) {
    console.error('Failed to cancel training job:', error);
    return { success: false };
  }
}

// Wake up a sleeping node via Wake-on-LAN
export async function wakeNode(macAddress: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${SWARM_API_BASE}/api/nodes/wake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac_address: macAddress }),
    });

    return await response.json();
  } catch (error) {
    console.error('Failed to wake node:', error);
    return { success: false };
  }
}

// Trigger network scan for new nodes
export async function scanForNodes(): Promise<{ success: boolean; nodes_found?: number }> {
  try {
    // Scan triggers a re-fetch of nodes, return success after checking nodes
    const nodesResponse = await fetch(`${SWARM_API_BASE}/api/nodes`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (nodesResponse.ok) {
      const data = await nodesResponse.json();
      return { success: true, nodes_found: data.nodes?.length || 0 };
    }

    return { success: false };
  } catch (error) {
    console.error('Failed to scan for nodes:', error);
    return { success: false };
  }
}
