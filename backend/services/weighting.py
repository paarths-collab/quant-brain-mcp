def equal_weights(equity_curves):
    n = len(equity_curves)
    return {k: 1/n for k in equity_curves}

def risk_parity_weights(equity_curves):
    vols = {
        k: v.pct_change().std()
        for k, v in equity_curves.items()
    }
    inv = {k: 1/v if v > 0 else 0 for k, v in vols.items()}
    total = sum(inv.values())
    return {k: v/total for k, v in inv.items()}
