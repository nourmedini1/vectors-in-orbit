"""
Reward calculation module for RL training.
Computes rewards from logged outcomes using position weights and action values.
"""

import logging
from typing import Dict, List, Any

import numpy as np

from config import RewardConfig

logger = logging.getLogger(__name__)


def calculate_reward(
    log: Dict[str, Any], 
    config: RewardConfig = None
) -> float:
    """
    Calculate reward from a single log entry.
    
    Reward formula:
    - If user interacted:
        reward = sum(position_weight[rank] * action_value[action] * revenue_multiplier)
    - If no interaction:
        reward = no_interaction_penalty
    
    Args:
        log: Log dictionary with 'outcomes' and 'ranking_metadata'
        config: Reward configuration (uses default if None)
        
    Returns:
        Computed reward value
    """
    if config is None:
        config = RewardConfig()
    
    outcomes = log.get('outcomes')
    if outcomes is None:
        outcomes = {}
    
    ranking_metadata = log.get('ranking_metadata', [])
    
    # Check if user took any action
    user_action = outcomes.get('user_action')
    if not user_action or user_action == 'none':
        return config.no_interaction_penalty
    
    # Get purchased ranks (can be multiple items)
    purchased_ranks = outcomes.get('purchased_ranks', [])
    if not purchased_ranks:
        return config.no_interaction_penalty
    
    # Calculate reward for each interaction
    total_reward = 0.0
    
    for rank in purchased_ranks:
        # Position weight (0-indexed internally)
        rank_idx = rank - 1  # Convert to 0-indexed
        if rank_idx < len(config.position_weights):
            position_weight = config.position_weights[rank_idx]
        else:
            # For ranks beyond defined weights, use minimum weight
            position_weight = config.position_weights[-1]
        
        # Action value
        action_value = config.action_values.get(user_action, 0.0)
        
        # Revenue multiplier (only for purchases)
        revenue_multiplier = 1.0
        if user_action == 'purchase' and ranking_metadata:
            try:
                # Get price of purchased item
                product_price = ranking_metadata[rank_idx].get('price', 0.0)
                # Scale by revenue (capped at max multiplier)
                revenue_multiplier = min(
                    product_price / config.revenue_scale, 
                    config.revenue_max_multiplier
                )
            except (IndexError, KeyError, ValueError) as e:
                logger.warning(f"Failed to get price for rank {rank}: {e}")
                revenue_multiplier = 1.0
        
        # Combine components
        interaction_reward = position_weight * action_value * revenue_multiplier
        total_reward += interaction_reward
    
    return total_reward


def add_rewards_to_logs(
    logs: List[Dict[str, Any]], 
    config: RewardConfig = None,
    overwrite: bool = False
) -> List[Dict[str, Any]]:
    """
    Add reward field to all logs.
    
    Args:
        logs: List of log dictionaries
        config: Reward configuration
        overwrite: Whether to overwrite existing rewards
        
    Returns:
        Logs with 'reward' field populated
    """
    if config is None:
        config = RewardConfig()
    
    computed = 0
    skipped = 0
    errors = 0
    
    for log in logs:
        # Skip if reward already exists and not overwriting
        if not overwrite and log.get('reward') is not None:
            skipped += 1
            continue
        
        try:
            reward = calculate_reward(log, config)
            log['reward'] = reward
            computed += 1
        except Exception as e:
            logger.warning(f"Failed to compute reward for log {log.get('log_id', 'unknown')}: {e}")
            log['reward'] = config.no_interaction_penalty  # Default penalty for errors
            errors += 1
    
    logger.info(f"Computed rewards for {computed} logs ({skipped} skipped, {errors} errors)")
    
    return logs


def analyze_reward_distribution(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze reward distribution across logs.
    
    Args:
        logs: List of log dictionaries with 'reward' field
        
    Returns:
        Dictionary with reward statistics
    """
    rewards = []
    for log in logs:
        reward = log.get('reward')
        if reward is not None and isinstance(reward, (int, float)):
            rewards.append(reward)
    
    if not rewards:
        logger.warning("No rewards found in logs")
        return {}
    
    rewards_array = np.array(rewards)
    
    stats = {
        'count': len(rewards),
        'mean': float(rewards_array.mean()),
        'std': float(rewards_array.std()),
        'min': float(rewards_array.min()),
        'max': float(rewards_array.max()),
        'median': float(np.median(rewards_array)),
        'percentiles': {
            '25th': float(np.percentile(rewards_array, 25)),
            '50th': float(np.percentile(rewards_array, 50)),
            '75th': float(np.percentile(rewards_array, 75)),
            '90th': float(np.percentile(rewards_array, 90)),
            '95th': float(np.percentile(rewards_array, 95)),
            '99th': float(np.percentile(rewards_array, 99)),
        },
        'distribution': {
            'negative': int((rewards_array < 0).sum()),
            'zero': int((rewards_array == 0).sum()),
            'positive': int((rewards_array > 0).sum()),
        },
        'quartile_ranges': {
            'Q1': float(np.percentile(rewards_array, 25)),
            'Q2': float(np.percentile(rewards_array, 50)),
            'Q3': float(np.percentile(rewards_array, 75)),
            'IQR': float(np.percentile(rewards_array, 75) - np.percentile(rewards_array, 25)),
        }
    }
    
    logger.info("Reward distribution analysis:")
    logger.info(f"  Count: {stats['count']}")
    logger.info(f"  Mean: {stats['mean']:.3f}")
    logger.info(f"  Std: {stats['std']:.3f}")
    logger.info(f"  Range: [{stats['min']:.3f}, {stats['max']:.3f}]")
    logger.info(f"  Median: {stats['median']:.3f}")
    logger.info(f"  Distribution: {stats['distribution']['negative']} negative, "
                f"{stats['distribution']['zero']} zero, {stats['distribution']['positive']} positive")
    
    return stats


def get_reward_breakdown_by_action(logs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Break down reward statistics by user action type.
    
    Args:
        logs: List of log dictionaries
        
    Returns:
        Dictionary mapping action types to their reward statistics
    """
    action_rewards = {}
    
    for log in logs:
        reward = log.get('reward')
        if reward is None or not isinstance(reward, (int, float)):
            continue
        
        outcomes = log.get('outcomes')
        if outcomes is None:
            outcomes = {}
        user_action = outcomes.get('user_action', 'none')
        
        if user_action not in action_rewards:
            action_rewards[user_action] = []
        
        action_rewards[user_action].append(reward)
    
    # Compute statistics for each action
    breakdown = {}
    for action, rewards in action_rewards.items():
        rewards_array = np.array(rewards)
        breakdown[action] = {
            'count': len(rewards),
            'mean': float(rewards_array.mean()),
            'std': float(rewards_array.std()),
            'min': float(rewards_array.min()),
            'max': float(rewards_array.max()),
            'median': float(np.median(rewards_array)),
        }
    
    logger.info("Reward breakdown by action:")
    for action, stats in breakdown.items():
        logger.info(f"  {action}: count={stats['count']}, mean={stats['mean']:.3f}, "
                    f"std={stats['std']:.3f}")
    
    return breakdown


def validate_reward_computation(logs: List[Dict[str, Any]], sample_size: int = 5) -> None:
    """
    Validate reward computation by printing sample calculations.
    
    Args:
        logs: List of log dictionaries
        sample_size: Number of samples to show
    """
    logger.info(f"Validating reward computation with {sample_size} samples:")
    
    config = RewardConfig()
    
    for i, log in enumerate(logs[:sample_size]):
        reward = log.get('reward')
        outcomes = log.get('outcomes')
        if outcomes is None:
            outcomes = {}
        user_action = outcomes.get('user_action', 'none')
        purchased_ranks = outcomes.get('purchased_ranks', [])
        
        logger.info(f"\n--- Sample {i + 1} ---")
        logger.info(f"Log ID: {log.get('log_id', 'unknown')}")
        logger.info(f"User Action: {user_action}")
        logger.info(f"Purchased Ranks: {purchased_ranks}")
        logger.info(f"Computed Reward: {reward:.3f}")
        
        # Show calculation breakdown
        if purchased_ranks:
            for rank in purchased_ranks:
                rank_idx = rank - 1
                position_weight = config.position_weights[rank_idx] if rank_idx < len(config.position_weights) else config.position_weights[-1]
                action_value = config.action_values.get(user_action, 0.0)
                
                logger.info(f"  Rank {rank}: pos_weight={position_weight:.2f}, "
                            f"action_value={action_value:.2f}")
        else:
            logger.info(f"  No interaction: penalty={config.no_interaction_penalty}")
