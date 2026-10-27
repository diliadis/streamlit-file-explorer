#!/usr/bin/env bash
#SBATCH --job-name=docking-example
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00

# Illustrative job file. Browsing never executes scripts.
python run_docking.py --config config.yaml
