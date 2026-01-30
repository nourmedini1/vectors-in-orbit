"""
Evaluation module for counterfactual and business metrics.
Includes IPS-based conversion rate, MRR, precision@k, and revenue metrics.
"""

import logging
from typing import Dict, List, Tuple, Callable, Any

import numpy as np
from scipy import stats

from config import EvaluationConfig

logger = logging.getLogger(__name__)


def compute_importance_weights(
    logged_actions: np.ndarray,
    rl_actions: np.ndarray,
    propensity_noise: float = 0.1,
    clip_max: float = 10.0,
) -> np.ndarray:
    """
    Compute importance sampling weights for counterfactual evaluation.
    
    Assumes both policies are continuous and use Gaussian noise for exploration.
    
    Args:
        logged_actions: Actions from logged policy, shape (n_samples, action_dim)
        rl_actions: Actions from RL policy, shape (n_samples, action_dim)
        propensity_noise: Assumed exploration noise std in logged policy
        clip_max: Maximum importance weight (for variance reduction)
        
    Returns:
        Importance weights, shape (n_samples,)
    """
    # Compute L2 distance between actions
    action_diff = np.linalg.norm(logged_actions - rl_actions, axis=1)
    
    # Approximate importance weight as ratio of Gaussian densities
    # π(a|s) / μ(a|s) ≈ exp(-||a_rl - a_log||^2 / (2σ^2))
    weights = np.exp(-action_diff ** 2 / (2 * propensity_noise ** 2))
    
    # Clip for variance reduction
    weights = np.clip(weights, 0, clip_max)
    
    return weights


def counterfactual_conversion_rate(
    logged_rewards: np.ndarray,
    logged_actions: np.ndarray,
    rl_actions: np.ndarray,
    config: EvaluationConfig = None,
) -> Tuple[float, Tuple[float, float]]:
    """
    Estimate counterfactual conversion rate using importance sampling.
    
    Conversion = fraction of sessions with positive reward (purchase).
    
    Args:
        logged_rewards: Rewards from logged data
        logged_actions: Actions from logged policy
        rl_actions: Actions from RL policy
        config: Evaluation configuration
        
    Returns:
        Tuple of (conversion_rate, confidence_interval)
    """
    if config is None:
        config = EvaluationConfig()
    
    # Compute importance weights
    weights = compute_importance_weights(
        logged_actions,
        rl_actions,
        propensity_noise=config.ips_propensity_noise,
        clip_max=config.ips_clip_max,
    )
    
    # Compute weighted conversion (positive reward = conversion)
    conversions = (logged_rewards > 0).astype(float)
    weighted_conversions = conversions * weights
    
    # IPS estimate
    conversion_rate = weighted_conversions.sum() / weights.sum()
    
    # Bootstrap confidence interval
    ci = bootstrap_confidence_interval(
        weighted_conversions,
        weights,
        n_bootstrap=config.bootstrap_samples,
        confidence=config.confidence_level,
    )
    
    logger.info(f"Counterfactual conversion rate: {conversion_rate:.4f} "
                f"(95% CI: [{ci[0]:.4f}, {ci[1]:.4f}])")
    
    return float(conversion_rate), ci


def bootstrap_confidence_interval(
    values: np.ndarray,
    weights: np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """
    Compute bootstrap confidence interval for weighted mean.
    
    Args:
        values: Value array
        weights: Weight array
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (e.g., 0.95 for 95% CI)
        
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    n = len(values)
    bootstrap_means = []
    
    for _ in range(n_bootstrap):
        # Sample with replacement
        indices = np.random.choice(n, size=n, replace=True)
        sample_values = values[indices]
        sample_weights = weights[indices]
        
        # Compute weighted mean
        if sample_weights.sum() > 0:
            mean = sample_values.sum() / sample_weights.sum()
        else:
            mean = 0.0
        
        bootstrap_means.append(mean)
    
    # Compute percentiles
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_means, alpha / 2 * 100)
    upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)
    
    return (float(lower), float(upper))


def mean_reciprocal_rank(logs: List[Dict[str, Any]]) -> float:
    """
    Compute Mean Reciprocal Rank (MRR) for purchased items.
    
    MRR = average of 1/rank for all purchases.
    
    Args:
        logs: List of log dictionaries with outcomes
        
    Returns:
        MRR score
    """
    reciprocal_ranks = []
    
    for log in logs:
        outcomes = log.get('outcomes', {})
        if outcomes is None:
            outcomes = {}
        purchased_ranks = outcomes.get('purchased_ranks', [])
        
        if purchased_ranks:
            # Take best rank (lowest rank number)
            best_rank = min(purchased_ranks)
            reciprocal_ranks.append(1.0 / best_rank)
    
    if not reciprocal_ranks:
        return 0.0
    
    mrr = np.mean(reciprocal_ranks)
    logger.info(f"Mean Reciprocal Rank: {mrr:.4f}")
    
    return float(mrr)


def precision_at_k(logs: List[Dict[str, Any]], k: int) -> float:
    """
    Compute Precision@k for purchases.
    
    Precision@k = fraction of sessions where purchase occurred in top k ranks.
    
    Args:
        logs: List of log dictionaries
        k: Rank cutoff
        
    Returns:
        Precision@k score
    """
    hits = 0
    total = 0
    
    for log in logs:
        outcomes = log.get('outcomes', {})
        if outcomes is None:
            outcomes = {}
        purchased_ranks = outcomes.get('purchased_ranks', [])
        
        if purchased_ranks:
            total += 1
            # Check if any purchase was in top k
            if any(rank <= k for rank in purchased_ranks):
                hits += 1
    
    if total == 0:
        return 0.0
    
    precision = hits / total
    logger.info(f"Precision@{k}: {precision:.4f}")
    
    return float(precision)


def revenue_per_session(logs: List[Dict[str, Any]]) -> float:
    """
    Compute average revenue per session.
    
    Args:
        logs: List of log dictionaries
        
    Returns:
        Average revenue
    """
    total_revenue = 0.0
    n_sessions = len(logs)
    
    for log in logs:
        outcomes = log.get('outcomes', {})
        if outcomes is None:
            outcomes = {}
        revenue = outcomes.get('purchased_total_value', 0.0)
        total_revenue += revenue
    
    avg_revenue = total_revenue / n_sessions if n_sessions > 0 else 0.0
    logger.info(f"Revenue per session: ${avg_revenue:.2f}")
    
    return float(avg_revenue)


def conversion_rate(logs: List[Dict[str, Any]]) -> float:
    """
    Compute simple conversion rate (fraction of sessions with purchases).
    
    Args:
        logs: List of log dictionaries
        
    Returns:
        Conversion rate
    """
    conversions = 0
    
    for log in logs:
        outcomes = log.get('outcomes', {})
        if outcomes is None:
            outcomes = {}
        user_action = outcomes.get('user_action')
        if user_action == 'purchase':
            conversions += 1
    
    rate = conversions / len(logs) if logs else 0.0
    logger.info(f"Conversion rate: {rate:.4f}")
    
    return float(rate)


def compute_all_metrics(logs: List[Dict[str, Any]], k_values: List[int] = None) -> Dict[str, Any]:
    """
    Compute all business metrics for a set of logs.
    
    Args:
        logs: List of log dictionaries
        k_values: List of k values for precision@k
        
    Returns:
        Dictionary with all metrics
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]
    
    metrics = {
        'n_sessions': len(logs),
        'conversion_rate': conversion_rate(logs),
        'mean_reciprocal_rank': mean_reciprocal_rank(logs),
        'revenue_per_session': revenue_per_session(logs),
        'precision_at_k': {},
    }
    
    for k in k_values:
        metrics['precision_at_k'][f'p@{k}'] = precision_at_k(logs, k)
    
    return metrics


def compare_policies(
    baseline_logs: List[Dict[str, Any]],
    rl_logs: List[Dict[str, Any]],
    baseline_actions: np.ndarray,
    rl_actions: np.ndarray,
    config: EvaluationConfig = None,
) -> Dict[str, Any]:
    """
    Compare baseline and RL policies using multiple metrics.
    
    Args:
        baseline_logs: Logs from baseline policy
        rl_logs: Logs from RL policy (or same logs with RL actions)
        baseline_actions: Actions from baseline policy
        rl_actions: Actions from RL policy
        config: Evaluation configuration
        
    Returns:
        Dictionary with comparison results
    """
    if config is None:
        config = EvaluationConfig()
    
    logger.info("Computing baseline metrics...")
    baseline_metrics = compute_all_metrics(baseline_logs, k_values=config.precision_k_values)
    
    logger.info("Computing RL metrics...")
    rl_metrics = compute_all_metrics(rl_logs, k_values=config.precision_k_values)
    
    # Counterfactual conversion rate
    logger.info("Computing counterfactual conversion rate...")
    baseline_rewards = np.array([log.get('reward', 0.0) for log in baseline_logs])
    cf_conversion, cf_ci = counterfactual_conversion_rate(
        baseline_rewards,
        baseline_actions,
        rl_actions,
        config=config,
    )
    
    # Compute improvements
    improvements = {}
    for metric in ['conversion_rate', 'mean_reciprocal_rank', 'revenue_per_session']:
        baseline_val = baseline_metrics[metric]
        rl_val = rl_metrics[metric]
        
        if baseline_val > 0:
            pct_improvement = ((rl_val - baseline_val) / baseline_val) * 100
        else:
            pct_improvement = 0.0
        
        improvements[metric] = {
            'baseline': baseline_val,
            'rl': rl_val,
            'absolute_improvement': rl_val - baseline_val,
            'percent_improvement': pct_improvement,
        }
    
    comparison = {
        'baseline_metrics': baseline_metrics,
        'rl_metrics': rl_metrics,
        'counterfactual_conversion': {
            'rate': cf_conversion,
            'confidence_interval': cf_ci,
        },
        'improvements': improvements,
    }
    
    # Log summary
    logger.info("\n=== Policy Comparison ===")
    for metric, values in improvements.items():
        logger.info(f"{metric}:")
        logger.info(f"  Baseline: {values['baseline']:.4f}")
        logger.info(f"  RL: {values['rl']:.4f}")
        logger.info(f"  Improvement: {values['percent_improvement']:+.2f}%")
    
    return comparison


def evaluate_trained_model(
    model,
    test_states: np.ndarray,
    test_actions: np.ndarray,
    test_rewards: np.ndarray,
    test_logs: List[Dict[str, Any]],
    config: EvaluationConfig = None,
) -> Dict[str, Any]:
    """
    Complete evaluation of a trained RL model.
    
    Args:
        model: Trained CQLModel instance
        test_states: Test state features
        test_actions: Test (logged) actions
        test_rewards: Test rewards
        test_logs: Test log dictionaries
        config: Evaluation configuration
        
    Returns:
        Dictionary with all evaluation results
    """
    if config is None:
        config = EvaluationConfig()
    
    logger.info("Evaluating trained model on test set...")
    
    # Predict actions using RL policy
    rl_actions = model.predict(test_states)
    
    # Compute business metrics
    test_metrics = compute_all_metrics(test_logs, k_values=config.precision_k_values)
    
    # Counterfactual evaluation
    cf_conversion, cf_ci = counterfactual_conversion_rate(
        test_rewards,
        test_actions,
        rl_actions,
        config=config,
    )
    
    # Policy evaluation (action similarity)
    action_mse = np.mean((rl_actions - test_actions) ** 2)
    action_mae = np.mean(np.abs(rl_actions - test_actions))
    
    results = {
        'test_metrics': test_metrics,
        'counterfactual_conversion': {
            'rate': cf_conversion,
            'confidence_interval': cf_ci,
        },
        'policy_similarity': {
            'action_mse': float(action_mse),
            'action_mae': float(action_mae),
        },
        'n_test_samples': len(test_states),
    }
    
    logger.info("\n=== Model Evaluation Results ===")
    logger.info(f"Test samples: {results['n_test_samples']}")
    logger.info(f"Conversion rate: {test_metrics['conversion_rate']:.4f}")
    logger.info(f"Counterfactual conversion: {cf_conversion:.4f} (95% CI: [{cf_ci[0]:.4f}, {cf_ci[1]:.4f}])")
    logger.info(f"MRR: {test_metrics['mean_reciprocal_rank']:.4f}")
    logger.info(f"Revenue/session: ${test_metrics['revenue_per_session']:.2f}")
    logger.info(f"Action MSE: {action_mse:.4f}")
    
    return results
