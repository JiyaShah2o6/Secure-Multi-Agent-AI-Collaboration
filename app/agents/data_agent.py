from __future__ import annotations

from typing import Optional

from app.data.customer_repository import (
    CustomerRepository,
    get_default_customer_repository,
)
from app.models.schemas import AgentResponse


class DataAgent:
    def __init__(
        self,
        approval_resolver=None,
        repository: Optional[CustomerRepository] = None,
    ) -> None:
        self.name = "AgentB"
        self._approval_resolver = approval_resolver
        self._repository = (
            repository if repository is not None else get_default_customer_repository()
        )

    def handle_request(
        self, approval_ticket, customer_id=None, requested_fields=None
    ) -> AgentResponse:
        """Read only a one-use request approved by the in-process Governance transport."""
        if not self._approval_resolver:
            return AgentResponse("blocked", {}, "A Governance approval is required.")

        try:
            request = self._approval_resolver(
                approval_ticket, customer_id=customer_id, requested_fields=requested_fields
            )
        except TypeError:
            request = self._approval_resolver(approval_ticket)

        if request is None:
            return AgentResponse("blocked", {}, "A Governance approval is required.")

        if customer_id is not None and request.customer_id != customer_id:
            return AgentResponse("blocked", {}, "Approval ticket does not match customer.")
        if requested_fields is not None and not set(requested_fields).issubset(
            set(request.requested_fields)
        ):
            return AgentResponse(
                "blocked", {}, "Approval ticket does not match requested fields."
            )

        # Validate customer exists in repository
        if not self._repository.customer_exists(request.customer_id):
            return AgentResponse("error", {}, "Customer not found")

        # Query minimal permitted fields through repository
        record = self._repository.get_record(
            request.customer_id, request.requested_fields
        )
        if record is None:
            return AgentResponse("error", {}, "Customer not found")

        # Enforce second projection to prevent over-retrieval
        response = {}
        for field in request.requested_fields:
            if field in record:
                response[field] = record[field]
            else:
                return AgentResponse(
                    "error", {}, "Approved field is unavailable in the customer schema."
                )

        return AgentResponse("success", response)
