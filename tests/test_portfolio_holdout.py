"""Chronological validation must never fit weights to evaluation observations."""
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from main import run_generate_optimized_verdict
from tools.backtesting.portfolio_bt import split_validation_history


def prices(n=300):
    rng = np.random.default_rng(12)
    return pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(.001, .01, (n, 2)), axis=0)),
                        columns=['A', 'B'], index=pd.bdate_range('2020-01-01', periods=n))


def test_split_is_disjoint_and_chronological():
    train, holdout, metadata = split_validation_history(prices())
    assert len(train) == 210
    assert len(holdout) == 90
    assert train.index.max() < holdout.index.min()
    assert metadata['method'] == 'chronological_holdout'


def test_short_history_has_actionable_error():
    with pytest.raises(ValueError, match='Insufficient history.*longer period'):
        split_validation_history(prices(90))


def test_optimizer_cannot_see_holdout_and_backtest_cannot_see_training():
    frame = prices()
    altered = frame.copy()
    altered.iloc[210:, 0] *= np.linspace(1, 10, 90)
    seen_moments = []
    seen_holdouts = []
    for source in [frame, altered]:
        def resolve(ticker, **kwargs):
            return pd.DataFrame({'Close': source[ticker]}), None, ticker
        def optimize(mu, covariance, **kwargs):
            seen_moments.append((mu.copy(), covariance.copy()))
            return {'weights': {'A': .5, 'B': .5}}
        def backtest(data, weights):
            seen_holdouts.append(data.copy())
            return {'portfolio_sharpe': 1.0, 'portfolio_total_return': '1%', 'portfolio_drawdown': '2%'}
        with patch('core.data_loader.resolve_ticker', side_effect=resolve), \
             patch('tools.optimization.mean_variance.run_mvo_basic', side_effect=optimize), \
             patch('tools.backtesting.portfolio_bt.backtest_optimized_portfolio', side_effect=backtest), \
             patch('main._compute_portfolio_intelligence', return_value=([], None)):
            result = run_generate_optimized_verdict(['A', 'B'], 10000)
        assert 'error' not in result
        assert result['validation']['training_observations'] == 210
    pd.testing.assert_series_equal(seen_moments[0][0], seen_moments[1][0])
    pd.testing.assert_frame_equal(seen_moments[0][1], seen_moments[1][1])
    pd.testing.assert_frame_equal(seen_holdouts[0], frame.iloc[210:])
    pd.testing.assert_frame_equal(seen_holdouts[1], altered.iloc[210:])


def test_negative_holdout_overrides_positive_full_history_alpha():
    frame = prices()
    frame.iloc[:210, :] = np.linspace(50, 300, 210)[:, None]
    frame.iloc[210:, :] = np.linspace(300, 200, 90)[:, None]
    # Full history is still strongly positive, while evaluation loses money.
    assert (frame.iloc[-1] > frame.iloc[0]).all()
    def resolve(ticker, **kwargs):
        return pd.DataFrame({'Close': frame[ticker]}), None, ticker
    blended = {'tickers_used': ['A'], 'coverage_weight': 1.0, 'alpha_annualized': .2,
               'beta': 1.0, 'r_squared': .5, 'one_day_var_95_pct': -1,
               'dominant_regime': 'TRENDING'}
    entries = [{'ticker': 'A', 'weight': 1.0, 'benchmark': '^GSPC',
                'quant_analysis': {}, 'alpha_analysis': {}}]
    with patch('core.data_loader.resolve_ticker', side_effect=resolve), \
         patch('tools.optimization.mean_variance.run_mvo_basic', return_value={'weights': {'A': 1.0}}), \
         patch('main._compute_portfolio_intelligence', return_value=(entries, blended)):
        result = run_generate_optimized_verdict(['A'], 10000)
    assert 'error' not in result
    assert result['backtest_metrics']['portfolio_sharpe'] < 0
    assert result['final_verdict'] == 'STAY AWAY'
    assert result['validation']['costs_modeled'] is False


@pytest.mark.parametrize('method', ['mvo', 'hrp', 'min_volatility', 'max_sharpe',
                                    'black_litterman', 'cvar', 'semivariance'])
def test_all_real_optimizers_complete_holdout(method):
    frame = prices(500)
    def resolve(ticker, **kwargs):
        return pd.DataFrame({'Close': frame[ticker]}), None, ticker
    with patch('core.data_loader.resolve_ticker', side_effect=resolve), \
         patch('main._compute_portfolio_intelligence', return_value=([], None)):
        result = run_generate_optimized_verdict(['A', 'B'], 10000, method)
    assert 'error' not in result, result
    assert result['validation']['training_observations'] == 350
    assert result['validation']['holdout_observations'] == 150
    assert result['optimization_method'] == method.upper()
