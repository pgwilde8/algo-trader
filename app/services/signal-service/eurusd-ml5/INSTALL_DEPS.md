# Installing Dependencies for Signal Service

The signal service requires additional ML libraries that need to be installed.

## Install Dependencies

From the algo-trader root directory:

```bash
cd /home/myalgo/algo-trader
source venv/bin/activate
pip install pandas numpy xgboost scikit-learn
```

Or install all requirements (which now includes ML dependencies):

```bash
cd /home/myalgo/algo-trader
source venv/bin/activate
pip install -r requirements.txt
```

## Required Packages

- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computing
- **xgboost** - XGBoost ML models
- **scikit-learn** - Machine learning utilities (for metrics)

These have been added to `requirements.txt` in the root directory.

