from pypfopt import DiscreteAllocation


def get_final_shopping_list(weights, latest_prices, total_amount=100000, allow_shorts=False):
    """
    STRATEGY: Converting percentages into actual share counts.
    WHEN TO USE: The final step before the user executes the trade.
    GREEDY ALGORITHM: Efficiently allocates shares based on available cash.
    SHORTS: If allow_shorts is True, it handles negative weights.
    """
    da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=total_amount)
    allocation, leftover = da.greedy_portfolio()

    return {
        "shares_to_buy": allocation,
        "uninvested_cash": f"{leftover:.2f}",
        "allow_shorts": allow_shorts,
    }
