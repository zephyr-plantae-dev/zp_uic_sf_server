class AIStudioError(Exception):
    """Base Exception for AI Studio System"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class BlueprintValidationError(AIStudioError):
    def __init__(self, details: str):
        super().__init__(f"Invalid Blueprint: {details}", 400, "BLUEPRINT_INVALID")

class ResourceNotFoundError(AIStudioError):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} not found: {resource_id}", 404, "NOT_FOUND")

class ExternalAPIError(AIStudioError):
    def __init__(self, service: str, details: str):
        super().__init__(f"External Service Error ({service}): {details}", 502, "EXTERNAL_API_FAIL")

class ContentPolicyError(AIStudioError):
    def __init__(self, reason: str):
        super().__init__(f"Content Policy Violation: {reason}", 422, "POLICY_VIOLATION")