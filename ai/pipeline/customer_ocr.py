class MockCustomerOcr:
    def read(self, _: object) -> tuple[str | None, float]:
        return None, 0.0
