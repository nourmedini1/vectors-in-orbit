"""
Data processing module for RL training.
Loads JSONL logs and extracts state/action features.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)


def load_logs(log_path: Path) -> List[Dict[str, Any]]:
    """
    Load logs from JSONL file.
    
    Args:
        log_path: Path to JSONL log file
        
    Returns:
        List of log dictionaries
    """
    logs = []
    with open(log_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                log = json.loads(line.strip())
                logs.append(log)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse line {line_num}: {e}")
                continue
    
    logger.info(f"Loaded {len(logs)} logs from {log_path}")
    return logs


def extract_state_vector(state_dict: Dict[str, Any], max_brands: int = 3, max_categories: int = 5) -> np.ndarray:
    """
    Extract state features into a flat numpy vector.
    
    State components:
    - User features: luxury_affinity, hesitation_count, purchase_count, category_diversity, 
                     top N brand affinities, top N category spends
    - Candidate features: count, price_mean, price_std, price_min, price_max, 
                          avg_desirability, discounted_count
    - Session features: query_length, query_has_brand (binary), query_has_price_terms (binary), 
                        previous_searches_count
    
    Args:
        state_dict: State dictionary from log
        max_brands: Number of top brands to include
        max_categories: Number of top categories to include
        
    Returns:
        Flat numpy array of state features
    """
    features = []
    
    # User features
    user_feats = state_dict.get('user_features', {})
    features.append(user_feats.get('luxury_affinity', 0.0))
    features.append(user_feats.get('hesitation_count', 0))
    features.append(user_feats.get('purchase_count', 0))
    features.append(user_feats.get('category_diversity', 0.0))
    
    # Top N brand affinities
    brand_affinity = user_feats.get('brand_affinity', {})
    top_brands = sorted(brand_affinity.items(), key=lambda x: x[1], reverse=True)[:max_brands]
    for i in range(max_brands):
        if i < len(top_brands):
            features.append(top_brands[i][1])
        else:
            features.append(0.0)
    
    # Top N category spends
    avg_category_spend = user_feats.get('avg_category_spend', {})
    top_categories = sorted(avg_category_spend.items(), key=lambda x: x[1], reverse=True)[:max_categories]
    for i in range(max_categories):
        if i < len(top_categories):
            features.append(top_categories[i][1])
        else:
            features.append(0.0)
    
    # Candidate features
    candidate_feats = state_dict.get('candidate_features', {})
    features.append(candidate_feats.get('count', 0))
    features.append(candidate_feats.get('price_mean', 0.0))
    features.append(candidate_feats.get('price_std', 0.0))
    features.append(candidate_feats.get('price_min', 0.0))
    features.append(candidate_feats.get('price_max', 0.0))
    features.append(candidate_feats.get('avg_desirability', 0.0))
    features.append(candidate_feats.get('discounted_count', 0))
    
    # Session features
    session_feats = state_dict.get('session_features', {})
    features.append(session_feats.get('query_length', 0))
    features.append(1.0 if session_feats.get('query_has_brand', False) else 0.0)
    features.append(1.0 if session_feats.get('query_has_price_terms', False) else 0.0)
    features.append(session_feats.get('previous_searches_count', 0))
    
    return np.array(features, dtype=np.float32)


def extract_action_vector(action_dict: Dict[str, Any], normalize: bool = True) -> np.ndarray:
    """
    Extract action weights into a numpy vector.
    
    Actions are the 7 weights: W_COLLAB_POS, W_COLLAB_NEG, W_TRAIT, W_BRAND, 
                                W_WISHLIST, W_MARKET_CONV, W_MARKET_DEAL
    
    Args:
        action_dict: Action dictionary from log
        normalize: Whether to normalize weights to [0, 1] and sum to 1
        
    Returns:
        Numpy array of action weights
    """
    weights = [
        action_dict.get('W_COLLAB_POS', 0.0),
        action_dict.get('W_COLLAB_NEG', 0.0),
        action_dict.get('W_TRAIT', 0.0),
        action_dict.get('W_BRAND', 0.0),
        action_dict.get('W_WISHLIST', 0.0),
        action_dict.get('W_MARKET_CONV', 0.0),
        action_dict.get('W_MARKET_DEAL', 0.0),
    ]
    
    action_vector = np.array(weights, dtype=np.float32)
    
    if normalize:
        # Normalize to [0, 1] range (original range is [0, 2])
        action_vector = np.clip(action_vector / 2.0, 0.0, 1.0)
        
        # Ensure sum to 1 (for probability-like interpretation)
        total = action_vector.sum()
        if total > 0:
            action_vector = action_vector / total
        else:
            # If all zeros, use uniform distribution
            action_vector = np.ones(7, dtype=np.float32) / 7.0
    
    return action_vector


def normalize_state_features(states: np.ndarray) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    Normalize state features using standardization (z-score).
    
    Args:
        states: Array of shape (n_samples, n_features)
        
    Returns:
        Tuple of (normalized_states, normalization_params)
        normalization_params contains 'mean' and 'std' arrays
    """
    mean = states.mean(axis=0)
    std = states.std(axis=0) + 1e-8  # Avoid division by zero
    
    normalized_states = (states - mean) / std
    
    normalization_params = {
        'mean': mean,
        'std': std
    }
    
    logger.info(f"Normalized states with shape {states.shape}")
    logger.info(f"Mean range: [{mean.min():.2f}, {mean.max():.2f}]")
    logger.info(f"Std range: [{std.min():.2f}, {std.max():.2f}]")
    
    return normalized_states, normalization_params


def prepare_dataset(
    logs: List[Dict[str, Any]], 
    normalize_states: bool = True,
    normalize_actions: bool = True,
    filter_rewards: bool = True,
    min_reward: float = -10.0,
    max_reward: float = 100.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Prepare complete dataset for d3rlpy from logs.
    
    Args:
        logs: List of log dictionaries (must have 'reward' field)
        normalize_states: Whether to normalize state features
        normalize_actions: Whether to normalize action weights
        filter_rewards: Whether to filter outlier rewards
        min_reward: Minimum reward threshold
        max_reward: Maximum reward threshold
        
    Returns:
        Tuple of (states, actions, rewards, metadata)
        - states: Array of shape (n_samples, state_dim)
        - actions: Array of shape (n_samples, 7)
        - rewards: Array of shape (n_samples,)
        - metadata: Dict with normalization params and stats
    """
    states_list = []
    actions_list = []
    rewards_list = []
    
    skipped = 0
    for log in logs:
        # Skip logs without rewards
        reward = log.get('reward')
        if reward is None:
            skipped += 1
            continue
        
        # Validate reward is a number
        if not isinstance(reward, (int, float)):
            skipped += 1
            continue
        
        # Filter outliers
        if filter_rewards and (reward < min_reward or reward > max_reward):
            skipped += 1
            continue
        
        try:
            state = extract_state_vector(log.get('state', {}))
            action = extract_action_vector(log.get('action', {}), normalize=normalize_actions)
            
            states_list.append(state)
            actions_list.append(action)
            rewards_list.append(reward)
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to extract features from log {log.get('log_id', 'unknown')}: {e}")
            skipped += 1
            continue
    
    if not states_list:
        raise ValueError("No valid samples found in logs")
    
    states = np.array(states_list, dtype=np.float32)
    actions = np.array(actions_list, dtype=np.float32)
    rewards = np.array(rewards_list, dtype=np.float32)
    
    metadata = {
        'n_samples': len(states),
        'skipped': skipped,
        'state_dim': states.shape[1],
        'action_dim': actions.shape[1],
    }
    
    # Normalize states
    if normalize_states:
        states, norm_params = normalize_state_features(states)
        metadata['normalization'] = norm_params
    
    # Compute statistics
    metadata['reward_stats'] = {
        'mean': float(rewards.mean()),
        'std': float(rewards.std()),
        'min': float(rewards.min()),
        'max': float(rewards.max()),
        'median': float(np.median(rewards)),
    }
    
    logger.info(f"Prepared dataset with {len(states)} samples ({skipped} skipped)")
    logger.info(f"State dim: {states.shape[1]}, Action dim: {actions.shape[1]}")
    logger.info(f"Reward stats: mean={rewards.mean():.2f}, std={rewards.std():.2f}, "
                f"min={rewards.min():.2f}, max={rewards.max():.2f}")
    
    return states, actions, rewards, metadata


def save_processed_logs(logs: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Save processed logs (with rewards) back to JSONL.
    
    Args:
        logs: List of log dictionaries
        output_path: Path to save processed logs
    """
    with open(output_path, 'w') as f:
        for log in logs:
            f.write(json.dumps(log) + '\n')
    
    logger.info(f"Saved {len(logs)} processed logs to {output_path}")


def load_processed_dataset(processed_logs_path: Path, **kwargs) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Load and prepare dataset from processed logs file.
    
    Args:
        processed_logs_path: Path to processed logs JSONL file
        **kwargs: Additional arguments for prepare_dataset
        
    Returns:
        Tuple of (states, actions, rewards, metadata)
    """
    logs = load_logs(processed_logs_path)
    return prepare_dataset(logs, **kwargs)
