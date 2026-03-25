from agents.agent_manager import AgentManager


class Agent1ExtractionService:
    def __init__(self) -> None:
        self.manager = AgentManager()

    def enrich_transactions(self, raw_transactions: list[str]) -> list[dict]:
        return self.manager.enrich_transactions(raw_transactions)
