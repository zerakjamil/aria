export default {
  intro(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('ARIA: SOVEREIGN EDGE AI', { y: top + h * 0.16, size: u * 6.5, color: 'accent', at: -1 });
    s.subtitle('Air-Gapped Personal Intelligence · Zero Cloud Egress', { y: top + h * 0.25, size: u * 3.0, at: 0.5 });

    s.box('Centralized Cloud Model\n\n• High Recurring API Costs\n• Private Telemetry Leaves Host\n• Dependent on Cloud Uptime', {
      id: 'cloud',
      x: s.cx - w * 0.26,
      y: top + h * 0.62,
      w: w * 0.40,
      h: h * 0.44,
      icon: 'server-crash',
      color: 'red',
      at: '#cloud',
    });

    s.box('Aria Sovereign Edge\n\n• 100% Offline Air-Gapped\n• Zero Data Leaves Device\n• $0 Operating Cost Forever', {
      id: 'edge',
      x: s.cx + w * 0.26,
      y: top + h * 0.62,
      w: w * 0.40,
      h: h * 0.44,
      icon: 'shield',
      color: 'teal',
      at: '#edge',
    });

    s.arrow('cloud', 'edge', { label: 'sovereign transition', labelSize: 26, color: 'accent', at: '#edge' });
  },

  hardware(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('EDGE HARDWARE ENVELOPE', { y: top + h * 0.14, size: u * 6.0, color: 'accent', at: 0 });
    s.subtitle('NVIDIA GeForce GTX 1650 Mobile · 4,096 MiB Physical VRAM Cap', { y: top + h * 0.22, size: u * 2.8, at: 0.5 });

    s.box('4,096 MiB Total VRAM', {
      id: 'vram',
      x: s.cx - w * 0.32,
      y: top + h * 0.38,
      w: w * 0.28,
      h: h * 0.16,
      icon: 'cpu',
      color: 'purple',
      at: '#specs',
    });

    s.box('50 Watt TGP Budget', {
      id: 'tgp',
      x: s.cx,
      y: top + h * 0.38,
      w: w * 0.28,
      h: h * 0.16,
      icon: 'zap',
      color: 'orange',
      at: '#specs',
    });

    s.box('100% Offline Edge', {
      id: 'offline',
      x: s.cx + w * 0.32,
      y: top + h * 0.38,
      w: w * 0.28,
      h: h * 0.16,
      icon: 'shield',
      color: 'teal',
      at: '#specs',
    });

    s.box('Inference Serving (2,142 MiB)\nOllama Q4_K_M GGUF Runtime', {
      id: 'inf',
      x: s.cx - w * 0.20,
      y: top + h * 0.68,
      w: w * 0.36,
      h: h * 0.24,
      icon: 'server',
      color: 'blue',
      at: '#split',
    });

    s.box('On-Device Training (2,098 MiB)\nSoup RAM Sharding + 4-bit LoRA', {
      id: 'train',
      x: s.cx + w * 0.20,
      y: top + h * 0.68,
      w: w * 0.36,
      h: h * 0.24,
      icon: 'refresh-cw',
      color: 'green',
      at: '#split',
    });

    s.note('Both configurations strictly respect the 4,096 MiB physical boundary', {
      x: s.cx,
      y: top + h * 0.88,
      size: 28,
      at: '#split',
    });
  },

  duel(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('THE REASONING DUEL', { y: top + h * 0.12, size: u * 6.0, color: 'accent', at: 0 });
    s.subtitle('Raw Small Base Model vs Aria Reflective Policy', { y: top + h * 0.19, size: u * 2.8, at: 0.5 });

    s.terminal([
      { cmd: 'python algorithm_solver.py', at: '#raw' },
      { out: 'NameError: name "List" is not defined', color: 'red', at: '#raw' },
      { out: 'FAILED: 0/1 invariants verified', color: 'red', at: '#raw' },
    ], {
      x: s.cx - w * 0.25,
      y: top + h * 0.58,
      w: w * 0.46,
      size: 26,
      title: 'Raw Qwen2.5-3B Base',
      at: '#raw',
    });

    s.terminal([
      { cmd: 'aria solve --verify', at: '#aria' },
      { out: '<thought> Invariant: inject typing </thought>', color: 'blue', at: '#aria' },
      { out: 'EXECUTION: SUCCESS (0.002s)', color: 'green', at: '#aria' },
      { out: 'PASSED: 40/40 benchmarks', color: 'green', at: '#aria' },
    ], {
      x: s.cx + w * 0.25,
      y: top + h * 0.58,
      w: w * 0.46,
      size: 26,
      title: 'Aria 3B Test-Time Reasoning',
      at: '#aria',
    });
  },

  sandbox(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('4-TIER AST BLAST-RADIUS FIREWALL', { y: top + h * 0.14, size: u * 5.8, color: 'accent', at: 0 });
    s.subtitle('Zero-Trust Static Analysis Before Subprocess Execution', { y: top + h * 0.22, size: u * 2.8, at: 0.5 });

    s.box('Python AST Parser & Execution Policy Engine', {
      id: 'parser',
      x: s.cx,
      y: top + h * 0.38,
      w: w * 0.55,
      h: h * 0.14,
      icon: 'shield',
      color: 'teal',
      at: '#firewall',
    });

    s.box('Tier 0: Pure Algo\nIn-memory calculations', {
      id: 't0',
      x: s.cx - w * 0.36,
      y: top + h * 0.68,
      w: w * 0.21,
      h: h * 0.24,
      color: 'blue',
      at: '#tiers',
    });

    s.box('Tier 1: Read-Only\n/proc & system diagnostics', {
      id: 't1',
      x: s.cx - w * 0.12,
      y: top + h * 0.68,
      w: w * 0.21,
      h: h * 0.24,
      color: 'teal',
      at: '#tiers',
    });

    s.box('Tier 2: Workspace\nIsolated file mutations', {
      id: 't2',
      x: s.cx + w * 0.12,
      y: top + h * 0.68,
      w: w * 0.21,
      h: h * 0.24,
      color: 'yellow',
      at: '#tiers',
    });

    s.box('Tier 3: BLOCKED\nrm -rf / raw sockets', {
      id: 't3',
      x: s.cx + w * 0.36,
      y: top + h * 0.68,
      w: w * 0.21,
      h: h * 0.24,
      color: 'red',
      at: '#tiers',
    });
  },

  reflexion(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('AUTONOMOUS REFLEXION & SELF-REPAIR', { y: top + h * 0.14, size: u * 5.8, color: 'accent', at: 0 });
    s.subtitle('Traceback Distillation Closes the In-Context Feedback Loop', { y: top + h * 0.22, size: u * 2.8, at: 0.5 });

    s.box('1. Execution Fault\nSubprocess Traceback', {
      id: 'f1',
      x: s.cx - w * 0.36,
      y: top + h * 0.55,
      w: w * 0.21,
      h: h * 0.25,
      icon: 'server-crash',
      color: 'red',
      at: 0.5,
    });

    s.box('2. Traceback Distiller\nIsolates Error & AST Line', {
      id: 'f2',
      x: s.cx - w * 0.12,
      y: top + h * 0.55,
      w: w * 0.21,
      h: h * 0.25,
      icon: 'cpu',
      color: 'purple',
      at: '#distill',
    });

    s.box('3. Reasoning Scratchpad\n<thought> Dynamic Patch', {
      id: 'f3',
      x: s.cx + w * 0.12,
      y: top + h * 0.55,
      w: w * 0.21,
      h: h * 0.25,
      icon: 'terminal',
      color: 'blue',
      at: '#loop',
    });

    s.box('4. Verified Pass (R = 1.0)\nDeterministic Recovery', {
      id: 'f4',
      x: s.cx + w * 0.36,
      y: top + h * 0.55,
      w: w * 0.21,
      h: h * 0.25,
      icon: 'shield',
      color: 'green',
      at: '#loop',
    });

    s.arrow('f1', 'f2', { at: '#distill' });
    s.arrow('f2', 'f3', { at: '#loop' });
    s.arrow('f3', 'f4', { color: 'green', at: '#loop' });
  },

  rlvr(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('PHASE 10: ON-DEVICE GRPO & RLVR', { y: top + h * 0.12, size: u * 6.0, color: 'accent', at: 0 });
    s.subtitle('Group Relative Policy Optimization with Verifiable Rewards', { y: top + h * 0.19, size: u * 2.8, at: 0.5 });

    s.bars([
      { label: 'R1', value: -0.58 },
      { label: 'R2', value: 0.22 },
      { label: 'R3', value: 1.73 },
      { label: 'R4', value: -0.58 },
    ], {
      x: s.cx - w * 0.22,
      y: top + h * 0.58,
      w: w * 0.44,
      h: h * 0.46,
      at: '#grpo',
    });

    s.box('Policy Optimization Metrics\n\n• Group Size: G = 4 Rollouts\n• Verifiable Reward: R ∈ {0, 1}\n• Normalized Adv: A = (r - μ) / σ\n• Loss: 3.36 -> 1.35 Convergence\n• 100% On-Device GTX 1650', {
      id: 'metrics',
      x: s.cx + w * 0.24,
      y: top + h * 0.58,
      w: w * 0.42,
      h: h * 0.46,
      icon: 'refresh-cw',
      color: 'teal',
      at: '#advantage',
    });
  },

  outro(s) {
    const { top, h, w } = s.safe;
    const u = Math.min(w, h) / 100;

    s.title('SOVEREIGN EDGE INTELLIGENCE', { y: top + h * 0.18, size: u * 7.0, color: 'accent', at: 0 });
    s.subtitle('Department of Information System Engineering · Erbil Polytechnic University', { y: top + h * 0.27, size: u * 3.0, at: 0.5 });

    s.box('109 / 109 Passing\nRegression Invariants', {
      id: 'b1',
      x: s.cx - w * 0.28,
      y: top + h * 0.60,
      w: w * 0.25,
      h: h * 0.30,
      icon: 'shield',
      color: 'green',
      at: '#emblem',
    });

    s.box('0 Bytes Cloud Egress\n100% Privacy Preserved', {
      id: 'b2',
      x: s.cx,
      y: top + h * 0.60,
      w: w * 0.25,
      h: h * 0.30,
      icon: 'lock',
      color: 'teal',
      at: '#emblem',
    });

    s.box('GTX 1650 4GB GPU\nConsumer Hardware Ready', {
      id: 'b3',
      x: s.cx + w * 0.28,
      y: top + h * 0.60,
      w: w * 0.25,
      h: h * 0.30,
      icon: 'cpu',
      color: 'purple',
      at: '#emblem',
    });

    s.burst({ x: s.cx, y: top + h * 0.50, at: '#emblem', count: 35 });
  },
};
