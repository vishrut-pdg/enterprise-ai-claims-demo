class MemoryService:
    def __init__(self, claim_service):
        self.claim_service = claim_service

    def retrieve(self, claim_id):
        return self.claim_service.get_previous_outcomes(claim_id)
