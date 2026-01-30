"""
Main training script for RL policy training.
Orchestrates the full pipeline: load → reward → extract → train → evaluate → save.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, default_config
from src.data_processing import load_logs, prepare_dataset, save_processed_logs
from src.reward import add_rewards_to_logs, analyze_reward_distribution, validate_reward_computation
from src.model import CQLModel
from src.evaluation import evaluate_trained_model
from src.visualize import create_all_plots


def setup_logging(log_level: str = "INFO", log_file: Path = None):
    """Setup logging configuration."""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )


def set_random_seeds(seed: int):
    """Set random seeds for reproducibility."""
    np.random.seed(seed)
    # torch.manual_seed(seed)  # Uncomment if using PyTorch directly
    logging.info(f"Set random seed to {seed}")


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(description="Train RL policy for search ranking")
    
    # Data arguments
    parser.add_argument('--input_logs', type=str, default=None,
                        help='Path to input logs JSONL file (default: from config)')
    parser.add_argument('--output_model', type=str, default=None,
                        help='Path to save trained model (default: from config)')
    
    # Training arguments
    parser.add_argument('--epochs', type=int, default=None,
                        help='Number of training epochs (default: from config)')
    parser.add_argument('--batch_size', type=int, default=None,
                        help='Batch size (default: from config)')
    parser.add_argument('--test_split', type=float, default=0.2,
                        help='Fraction of data for testing (default: 0.2)')
    parser.add_argument('--val_split', type=float, default=0.2,
                        help='Fraction of training data for validation (default: 0.2)')
    
    # Model arguments
    parser.add_argument('--actor_lr', type=float, default=None,
                        help='Actor learning rate (default: from config)')
    parser.add_argument('--critic_lr', type=float, default=None,
                        help='Critic learning rate (default: from config)')
    parser.add_argument('--conservative_weight', type=float, default=None,
                        help='CQL conservative weight (default: from config)')
    
    # Flags
    parser.add_argument('--skip_reward_computation', action='store_true',
                        help='Skip reward computation (assumes rewards already in logs)')
    parser.add_argument('--save_processed_logs', action='store_true',
                        help='Save logs with computed rewards to processed_logs.jsonl')
    parser.add_argument('--no_normalize', action='store_true',
                        help='Disable state normalization')
    
    # Logging
    parser.add_argument('--log_level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Logging level')
    parser.add_argument('--log_file', type=str, default=None,
                        help='Path to log file (optional)')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path(args.log_file) if args.log_file else None
    setup_logging(args.log_level, log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("RL Policy Training Pipeline")
    logger.info("=" * 80)
    
    # Load configuration
    config = default_config
    
    # Override config with CLI arguments
    if args.input_logs:
        config.paths.raw_logs = Path(args.input_logs)
    if args.output_model:
        config.paths.cql_model = Path(args.output_model)
    if args.epochs:
        config.model.n_epochs = args.epochs
    if args.batch_size:
        config.model.batch_size = args.batch_size
    if args.actor_lr:
        config.model.actor_learning_rate = args.actor_lr
    if args.critic_lr:
        config.model.critic_learning_rate = args.critic_lr
    if args.conservative_weight:
        config.model.conservative_weight = args.conservative_weight
    
    config.data.test_size = args.test_split
    config.data.normalize_states = not args.no_normalize
    
    # Set random seeds
    set_random_seeds(config.data.random_seed)
    
    # Step 1: Load logs
    logger.info("\nStep 1: Loading logs...")
    logger.info(f"Input logs: {config.paths.raw_logs}")
    
    if not config.paths.raw_logs.exists():
        logger.error(f"Input logs file not found: {config.paths.raw_logs}")
        sys.exit(1)
    
    logs = load_logs(config.paths.raw_logs)
    logger.info(f"Loaded {len(logs)} logs")
    
    # Step 2: Compute rewards
    if not args.skip_reward_computation:
        logger.info("\nStep 2: Computing rewards...")
        logs = add_rewards_to_logs(logs, config.reward, overwrite=True)
        
        # Analyze reward distribution
        reward_stats = analyze_reward_distribution(logs)
        
        # Validate with samples
        validate_reward_computation(logs, sample_size=3)
        
        # Save processed logs if requested
        if args.save_processed_logs:
            logger.info(f"Saving processed logs to {config.paths.processed_logs}")
            save_processed_logs(logs, config.paths.processed_logs)
    else:
        logger.info("\nStep 2: Skipping reward computation (using existing rewards)")
    
    # Step 3: Prepare dataset
    logger.info("\nStep 3: Preparing dataset...")
    states, actions, rewards, metadata = prepare_dataset(
        logs,
        normalize_states=config.data.normalize_states,
        normalize_actions=config.data.normalize_actions,
        filter_rewards=True,
        min_reward=config.data.min_reward,
        max_reward=config.data.max_reward,
    )
    
    logger.info(f"Dataset prepared: {len(states)} samples")
    logger.info(f"State dimension: {states.shape[1]}")
    logger.info(f"Action dimension: {actions.shape[1]}")
    logger.info(f"Reward range: [{rewards.min():.2f}, {rewards.max():.2f}]")
    
    # Step 4: Train/test split
    logger.info("\nStep 4: Splitting train/test sets...")
    n_samples = len(states)
    n_test = int(n_samples * config.data.test_size)
    n_train = n_samples - n_test
    
    # Shuffle indices
    indices = np.random.permutation(n_samples)
    train_indices = indices[:n_train]
    test_indices = indices[n_train:]
    
    train_states = states[train_indices]
    train_actions = actions[train_indices]
    train_rewards = rewards[train_indices]
    
    test_states = states[test_indices]
    test_actions = actions[test_indices]
    test_rewards = rewards[test_indices]
    
    # Get test logs for evaluation
    test_logs = [logs[i] for i in test_indices]
    
    logger.info(f"Train set: {len(train_states)} samples")
    logger.info(f"Test set: {len(test_states)} samples")
    
    # Step 5: Train model
    logger.info("\nStep 5: Training CQL model...")
    model = CQLModel(config=config.model)
    
    training_metrics = model.train(
        train_states,
        train_actions,
        train_rewards,
        validation_split=args.val_split,
        n_epochs=config.model.n_epochs,
        n_steps_per_epoch=config.model.n_steps_per_epoch,
    )
    
    logger.info("Training completed")
    
    # Step 6: Evaluate model
    logger.info("\nStep 6: Evaluating model on test set...")
    evaluation_results = evaluate_trained_model(
        model,
        test_states,
        test_actions,
        test_rewards,
        test_logs,
        config=config.evaluation,
    )
    
    # Step 7: Save model
    logger.info("\nStep 7: Saving model...")
    model.save(config.paths.cql_model)
    logger.info(f"Model saved to {config.paths.cql_model}")
    
    # Step 8: Save results
    logger.info("\nStep 8: Saving results...")
    results = {
        'config': {
            'n_epochs': config.model.n_epochs,
            'batch_size': config.model.batch_size,
            'actor_lr': config.model.actor_learning_rate,
            'critic_lr': config.model.critic_learning_rate,
            'conservative_weight': config.model.conservative_weight,
        },
        'n_samples': n_samples,
        'train_samples': n_train,
        'test_samples': n_test,
        'n_epochs': config.model.n_epochs,
        'dataset': {
            'n_total': n_samples,
            'n_train': n_train,
            'n_test': n_test,
            'state_dim': int(states.shape[1]),
            'action_dim': int(actions.shape[1]),
        },
        'training_history': training_metrics.get('training_history', []),
        'training_metrics': training_metrics,
        'evaluation_metrics': {
            'conversion_rate': evaluation_results['test_metrics']['conversion_rate'],
            'counterfactual_conversion_rate': evaluation_results['counterfactual_conversion']['rate'],
            'mean_reciprocal_rank': evaluation_results['test_metrics']['mean_reciprocal_rank'],
            'revenue_per_session': evaluation_results['test_metrics']['revenue_per_session'],
            'action_mse': evaluation_results['policy_similarity']['action_mse'],
        },
        'evaluation_results': evaluation_results,
    }
    
    # Save results to JSON
    results_file = config.paths.results_dir / 'training_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {results_file}")
    
    # Step 9: Generate visualization plots
    logger.info("\nStep 9: Generating visualization plots...")
    try:
        plot_paths = create_all_plots(config.paths.results_dir, show_plots=False)
        for plot_name, plot_path in plot_paths.items():
            logger.info(f"  Created {plot_name}: {plot_path}")
    except Exception as e:
        logger.warning(f"Failed to generate plots: {e}")
        logger.warning("Continuing without plots...")
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("Training Summary")
    logger.info("=" * 80)
    logger.info(f"Total samples: {n_samples}")
    logger.info(f"Train samples: {n_train}")
    logger.info(f"Test samples: {n_test}")
    logger.info(f"Epochs trained: {config.model.n_epochs}")
    logger.info(f"Model saved: {config.paths.cql_model}")
    logger.info("\nTest Set Performance:")
    logger.info(f"  Conversion rate: {evaluation_results['test_metrics']['conversion_rate']:.4f}")
    logger.info(f"  Counterfactual conversion: {evaluation_results['counterfactual_conversion']['rate']:.4f}")
    logger.info(f"  MRR: {evaluation_results['test_metrics']['mean_reciprocal_rank']:.4f}")
    logger.info(f"  Revenue/session: ${evaluation_results['test_metrics']['revenue_per_session']:.2f}")
    logger.info("=" * 80)
    
    logger.info("\nTraining pipeline completed successfully!")


if __name__ == '__main__':
    main()
