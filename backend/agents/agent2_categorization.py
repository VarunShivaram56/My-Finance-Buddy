from agents.agent_manager import AgentManager


class Agent2CategorizationService:
    def __init__(self) -> None:
        self.manager = AgentManager()

    def categorize_merchants(self, merchants: list[str]) -> list[str]:
        return self.manager.categorize_batch(merchants)
