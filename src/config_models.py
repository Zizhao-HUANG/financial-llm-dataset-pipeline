from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class InterfaceConfig(BaseModel):
    """Pydantic model for a single interface configuration."""
    id: str
    source_domain: str
    freq: str
    scope: str
    avail_rule: str
    params: Optional[List[str]] = []
    columns_map: Optional[Dict[str, str]] = {}
    bootstrap_source: Optional[str] = None

class InterfacesConfig(BaseModel):
    """Pydantic model for the list of interfaces."""
    interfaces: List[InterfaceConfig]

class DomainRateLimitConfig(BaseModel):
    """Pydantic model for a single domain's rate limit settings."""
    domain: str
    rate: float
    capacity: int
    retry: int
    concurrency: int

class RateLimitsConfig(BaseModel):
    """Pydantic model for the rate limits configuration."""
    domains: List[DomainRateLimitConfig]

class SplitConfig(BaseModel):
    """Pydantic model for the train/validation/test split dates."""
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str

class ProjectConfigs(BaseModel):
    """A container for all validated configuration objects."""
    interfaces: InterfacesConfig
    rate_limits: RateLimitsConfig
    split: SplitConfig
    features_schema: Dict[str, Any] # Not strictly modeled for now
