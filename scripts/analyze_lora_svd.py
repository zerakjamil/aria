#!/usr/bin/env python3
"""
Singular Value Decomposition (SVD) and Rank Capacity Analysis
Evaluates the raw weight matrices of adapter_model.safetensors across
all 72 adapted attention projections (q_proj, v_proj for layers 0-35).
"""

import sys
import json
import argparse
from pathlib import Path
import torch
import numpy as np
from safetensors import safe_open


def analyze_adapter_svd(safetensors_path: str, config_path: str = None):
    p = Path(safetensors_path)
    if not p.exists():
        raise FileNotFoundError(f"Safetensors file not found at: {safetensors_path}")

    # Load config if available
    alpha = 16.0
    r = 16.0
    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            cfg = json.load(f)
            alpha = float(cfg.get("lora_alpha", 16.0))
            r = float(cfg.get("r", 16.0))
    scale = alpha / r

    print(f"=" * 90)
    print(f"ARIA LORA SVD & SPECTRUM ANALYSIS")
    print(f"Source: {safetensors_path}")
    print(f"Hyperparameters: rank={int(r)}, lora_alpha={int(alpha)}, scaling_factor={scale:.4f}")
    print(f"=" * 90)

    results = []
    
    with safe_open(safetensors_path, framework="pt", device="cpu") as f:
        keys = list(f.keys())
        
        # Identify layers
        num_layers = 36
        modules = ["q_proj", "v_proj"]
        
        for layer_idx in range(num_layers):
            for mod in modules:
                # Key patterns
                # base_model.model.model.layers.{i}.self_attn.{mod}.lora_A.weight
                # base_model.model.model.layers.{i}.self_attn.{mod}.lora_B.weight
                key_a = f"base_model.model.model.layers.{layer_idx}.self_attn.{mod}.lora_A.weight"
                key_b = f"base_model.model.model.layers.{layer_idx}.self_attn.{mod}.lora_B.weight"
                
                if key_a not in keys or key_b not in keys:
                    # Alternative pattern
                    matches_a = [k for k in keys if f"layers.{layer_idx}." in k and f"{mod}.lora_A" in k]
                    matches_b = [k for k in keys if f"layers.{layer_idx}." in k and f"{mod}.lora_B" in k]
                    if matches_a and matches_b:
                        key_a = matches_a[0]
                        key_b = matches_b[0]
                    else:
                        continue
                
                weight_a = f.get_tensor(key_a).float() # [r, d_in]
                weight_b = f.get_tensor(key_b).float() # [d_out, r]
                
                # Delta W = (alpha / r) * (B @ A)
                delta_w = scale * torch.matmul(weight_b, weight_a) # [d_out, d_in]
                
                # Compute singular values
                # delta_w rank is at most min(r, d_out, d_in) = 16
                s = torch.linalg.svdvals(delta_w) # Sorted descending
                sigmas = s[:int(r)].cpu().numpy()
                
                sigma_1 = float(sigmas[0])
                sigma_16 = float(sigmas[-1]) if len(sigmas) >= int(r) else 0.0
                
                # Condition number kappa = sigma_1 / sigma_16
                cond_num = sigma_1 / (sigma_16 + 1e-12)
                
                # Effective rank (Entropy-based: exp(-sum(p_i * ln(p_i))))
                sum_sigmas = np.sum(sigmas)
                if sum_sigmas > 1e-12:
                    p_i = sigmas / sum_sigmas
                    p_i_clean = p_i[p_i > 1e-12]
                    entropy = -np.sum(p_i_clean * np.log(p_i_clean))
                    eff_rank = float(np.exp(entropy))
                else:
                    eff_rank = 0.0
                
                # Stable rank = ||W||_F^2 / ||W||_2^2 = sum(sigma^2) / sigma_1^2
                stable_rank = float(np.sum(sigmas**2) / (sigma_1**2 + 1e-12))
                
                # Top-4 energy ratio
                top4_energy = float(np.sum(sigmas[:4]) / (sum_sigmas + 1e-12))
                
                # Frobenius norm
                frob_norm = float(torch.norm(delta_w, p="fro").item())
                
                results.append({
                    "layer": layer_idx,
                    "module": mod,
                    "d_out": weight_b.shape[0],
                    "d_in": weight_a.shape[1],
                    "sigma_1": sigma_1,
                    "sigma_2": float(sigmas[1]) if len(sigmas) > 1 else 0.0,
                    "sigma_4": float(sigmas[3]) if len(sigmas) > 3 else 0.0,
                    "sigma_8": float(sigmas[7]) if len(sigmas) > 7 else 0.0,
                    "sigma_16": sigma_16,
                    "sigmas": sigmas.tolist(),
                    "cond_num": cond_num,
                    "eff_rank": eff_rank,
                    "stable_rank": stable_rank,
                    "top4_energy": top4_energy,
                    "frob_norm": frob_norm,
                })

    print(f"Total analyzed projections: {len(results)} / 72")
    print("-" * 90)
    print(f"{'Layer':<6} {'Mod':<7} {'||dW||_F':<9} {'sigma_1':<9} {'sigma_4':<9} {'sigma_16':<10} {'kappa (cond)':<12} {'r_eff':<8} {'r_stable':<8}")
    print("-" * 90)

    # Print representative layers (every 4th layer + first and last)
    sample_layers = [0, 1, 4, 8, 12, 16, 20, 24, 28, 32, 35]
    for r_entry in results:
        if r_entry["layer"] in sample_layers:
            print(f"{r_entry['layer']:<6} {r_entry['module']:<7} {r_entry['frob_norm']:<9.4f} "
                  f"{r_entry['sigma_1']:<9.4f} {r_entry['sigma_4']:<9.4f} {r_entry['sigma_16']:<10.6f} "
                  f"{r_entry['cond_num']:<12.2f} {r_entry['eff_rank']:<8.2f} {r_entry['stable_rank']:<8.2f}")

    print("-" * 90)
    
    # Statistical summaries
    for mod in ["q_proj", "v_proj"]:
        mod_results = [r for r in results if r["module"] == mod]
        eff_ranks = [r["eff_rank"] for r in mod_results]
        cond_nums = [r["cond_num"] for r in mod_results]
        frob_norms = [r["frob_norm"] for r in mod_results]
        top4_energies = [r["top4_energy"] for r in mod_results]
        sigma_1s = [r["sigma_1"] for r in mod_results]
        sigma_16s = [r["sigma_16"] for r in mod_results]
        
        print(f"\nAGGREGATE METRICS FOR [{mod.upper()}] (N={len(mod_results)} projections):")
        print(f"  Effective Rank (r_eff):  mean={np.mean(eff_ranks):.3f} +/- {np.std(eff_ranks):.3f} "
              f"[min={np.min(eff_ranks):.3f}, max={np.max(eff_ranks):.3f}] (theoretical max: 16.0)")
        print(f"  Condition Number (kappa):mean={np.mean(cond_nums):.2f} +/- {np.std(cond_nums):.2f} "
              f"[min={np.min(cond_nums):.2f}, max={np.max(cond_nums):.2f}]")
        print(f"  Frobenius Norm (||dW||): mean={np.mean(frob_norms):.4f} +/- {np.std(frob_norms):.4f}")
        print(f"  Top-4 Energy Ratio:      mean={np.mean(top4_energies)*100:.2f}% +/- {np.std(top4_energies)*100:.2f}%")
        print(f"  Leading SingVal (sigma_1): mean={np.mean(sigma_1s):.4f} | Tail (sigma_16): mean={np.mean(sigma_16s):.6f}")

    # Overall diagnosis
    all_eff_ranks = [r["eff_rank"] for r in results]
    all_cond_nums = [r["cond_num"] for r in results]
    all_top4 = [r["top4_energy"] for r in results]
    mean_eff = np.mean(all_eff_ranks)
    mean_cond = np.mean(all_cond_nums)

    print("\n" + "=" * 90)
    print("MECHANISTIC ARCHITECTURAL DIAGNOSIS:")
    print(f"  Overall Mean Effective Rank: {mean_eff:.2f} / 16.0 ({mean_eff/16.0*100:.1f}% capacity utilization)")
    print(f"  Overall Mean Condition Number: {mean_cond:.2f}")
    
    if mean_eff < 3.0 or mean_cond > 5000:
        diagnosis = "CRITICAL: RANK COLLAPSE. Weight update is dominated by 1-2 singular vectors; r=16 is largely wasted."
    elif mean_eff >= 15.5 and np.mean([r["sigma_16"] for r in results]) / np.mean([r["sigma_1"] for r in results]) > 0.7:
        diagnosis = "UNDER-CAPACITY: Spectrum is completely flat without decay; r=16 bottlenecks expressive capacity."
    else:
        diagnosis = "HEALTHY LOW-RANK MANIFOLD: Optimal power-law spectral decay with substantial effective dimensionality. Neither rank collapse nor under-capacity is observed."
    
    print(f"  Diagnosis: {diagnosis}")
    print("=" * 90)

    # Save complete JSON report
    out_json = p.parent / "svd_rank_analysis.json"
    with open(out_json, "w") as f:
        json.dump({
            "hyperparameters": {"rank": r, "alpha": alpha, "scaling": scale},
            "summary": {
                "total_projections": len(results),
                "mean_effective_rank": float(mean_eff),
                "mean_condition_number": float(mean_cond),
                "diagnosis": diagnosis,
            },
            "projections": results
        }, f, indent=2)
    print(f"Saved complete SVD spectrum dataset to: {out_json}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoRA SVD Analysis")
    parser.add_argument("--adapter", default="/srv/storage/ai-companion/training/output/adapter_model.safetensors")
    parser.add_argument("--config", default="/srv/storage/ai-companion/training/output/adapter_config.json")
    args = parser.parse_args()
    analyze_adapter_svd(args.adapter, args.config)
