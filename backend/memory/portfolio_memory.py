class PortfolioMemory:

    def __init__(self):
        self.portfolios = {}

    def update(self, user_id, portfolio):
        self.portfolios[user_id] = portfolio

    def get(self, user_id):
        return self.portfolios.get(user_id, {})
