import pytest
import math
from scripts.grpo_self_evolution import compute_grpo_advantages

def test_grpo_advantages_uniform_failure():
    # If all 4 candidates fail (-1.0), std is 0 and advantage is 0
    rewards = [-1.0, -1.0, -1.0, -1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert mean_r == -1.0
    assert std_r == 0.0
    for a in advantages:
        assert abs(a) < 1e-3

def test_grpo_advantages_uniform_pass():
    # If all 4 candidates pass (+1.0), std is 0 and advantage is 0
    rewards = [1.0, 1.0, 1.0, 1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert mean_r == 1.0
    assert std_r == 0.0
    for a in advantages:
        assert abs(a) < 1e-3

def test_grpo_advantages_contrastive_one_winner():
    # One winner (+1.0) and three failures (-1.0)
    rewards = [-1.0, 1.0, -1.0, -1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert mean_r == -0.5
    assert abs(std_r - 0.866) < 1e-2
    # Winner must have high positive advantage (~1.73)
    assert advantages[1] > 1.70
    # Losers must have negative advantage (~ -0.58)
    assert advantages[0] < -0.50
    assert advantages[2] < -0.50
    assert advantages[3] < -0.50

def test_grpo_advantages_split():
    # Two winners, two losers
    rewards = [1.0, -1.0, 1.0, -1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert mean_r == 0.0
    assert abs(std_r - 1.0) < 1e-3
    assert abs(advantages[0] - 1.0) < 1e-3
    assert abs(advantages[1] - (-1.0)) < 1e-3
