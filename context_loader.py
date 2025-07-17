import random
from faker import Faker
from typing import Dict, Any
from nanoid import generate


class ContextLoader:
    """
    Mock loader for tenant context data using Faker for randomness.
    """
    def __init__(self, seed: int = None):
        """
        :param seed: Optional seed for reproducible data.
        """
        self.faker = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        # A small pool of example maintenance issues
        self._issues = [
            "Clogged sink",
            "Leaky faucet",
            "Heating not working",
            "Broken window lock",
            "Air conditioning issue",
            "Electrical outlet malfunction",
            "Toilet not flushing",
            "Pest infestation"
        ]
        self._statuses = ["open", "in_progress", "resolved"]

    def load(self, tenant_name: str, address: str) -> Dict[str, Any]:
        """
        Return a dict of contextual info with randomized values.
        """
        # 1. Rent balance: random between $800–$3,500
        balance_value = random.randint(800, 3500)
        rent_balance = f"${balance_value:,}"
        property_manager = self.faker.name()

        # 2. Lease end date: between 30 and 365 days from today
        lease_end_date = self.faker.date_between(
            start_date='+30d', end_date='+365d'
        ).isoformat()

        # 3. Maintenance history: 1–3 random past tickets
        history = []
        for _ in range(random.randint(1, 3)):
            issue = random.choice(self._issues)
            status = random.choice(self._statuses)
            # a date in the past year
            date = self.faker.date_between(
                start_date='-365d', end_date='today'
            ).isoformat()
            ticket_id = generate('1234567890abcdef', 10)
            history.append({
                "id": ticket_id,
                "issue": issue,
                "status": status,
                "date": date
            })

        return {
            "tenant_name": tenant_name,
            "address": address,
            "rent_balance": rent_balance,
            "lease_end_date": lease_end_date,
            "maintenance_history": history,
            "property_manager": property_manager
        }