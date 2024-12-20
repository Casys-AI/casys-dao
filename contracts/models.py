from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from algosdk import encoding
from datetime import datetime

class CaSysTokenConfig(BaseModel):
    """Configuration for CaSys Token"""
    total_supply: int = Field(..., description="Total supply of tokens", gt=0)
    decimals: int = Field(6, description="Number of decimals", ge=0, le=19)
    unit_name: str = Field("CSYS", description="Token unit name")
    asset_name: str = Field("CaSys Token", description="Token asset name")
    manager: str = Field(..., description="Manager address")
    reserve: Optional[str] = None
    freeze: Optional[str] = None
    clawback: Optional[str] = None
    url: Optional[str] = None
    metadata_hash: Optional[bytes] = None

    @field_validator('manager', 'reserve', 'freeze', 'clawback')
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                encoding.decode_address(v)
            except Exception as e:
                raise ValueError(f"Invalid Algorand address: {e}")
        return v

class CaSysBondConfig(BaseModel):
    """Configuration for CaSys Bond"""
    token_id: int = Field(..., description="Token ID", gt=0)
    amount: int = Field(..., description="Bond amount")
    interest_rate: float = Field(..., description="Annual interest rate in percentage", ge=0, le=100)
    maturity_date: int = Field(..., description="Maturity date (Unix timestamp)")
    collateral_ratio: int = Field(130, description="Collateral ratio in percentage", ge=0, le=10000)
    minimum_investment: int = Field(default=1000)
    maximum_investment: Optional[int] = None

class CaSysBond(BaseModel):
    """CaSys Bond Details"""
    id: int
    holder: str
    amount: int
    issue_date: datetime
    maturity_date: datetime
    interest_rate: int
    claimed: bool = False

    @field_validator('holder')
    def validate_holder_address(cls, v: str) -> str:
        try:
            encoding.decode_address(v)
        except Exception as e:
            raise ValueError(f"Invalid holder address: {e}")
        return v

class CaSysDAOConfig(BaseModel):
    """Configuration for CaSys DAO"""
    token_id: int = Field(..., description="Token ID", gt=0)
    quorum: int = Field(51, description="Quorum percentage required for proposals", gt=0)
    voting_period: int = Field(86400, description="Voting period in seconds", gt=0)
    execution_delay: int = Field(43200, description="Execution delay in seconds", gt=0)
    proposal_threshold: int = Field(..., description="Minimum tokens to create proposal", gt=0)

class CaSysProposalConfig(BaseModel):
    """Configuration for CaSys Proposal"""
    title: str = Field(..., description="Proposal title")
    description: str = Field(..., description="Proposal description")
    action_type: str = Field(..., description="Type of action to execute")
    action_data: Dict[str, Any] = Field(..., description="Action parameters")

class CaSysProposal(BaseModel):
    """CaSys DAO Proposal"""
    id: int
    creator: str
    title: str
    description: str
    start_time: int
    end_time: int
    execution_time: int
    executed: bool = False
    votes_for: int = 0
    votes_against: int = 0

    @field_validator('creator')
    def validate_creator_address(cls, v: str) -> str:
        try:
            encoding.decode_address(v)
        except Exception as e:
            raise ValueError(f"Invalid creator address: {e}")
        return v

    def is_active(self, current_time: int) -> bool:
        return self.start_time <= current_time < self.end_time

    def can_execute(self, current_time: int) -> bool:
        return not self.executed and current_time >= self.execution_time

class CaSysCollateralConfig(BaseModel):
    """Configuration for CaSys Collateral System"""
    stablecoin_id: int = Field(..., description="Stablecoin ID", gt=0)
    token_id: int = Field(..., description="Token ID", gt=0)
    collateral_ratio: int = Field(..., description="Collateral ratio in percentage", ge=0, le=10000)
    distribution_rate: int = Field(..., description="Distribution rate in percentage", ge=0, le=1000)
    distribution_period: int = Field(..., description="Distribution period in seconds", gt=0)
    manager_address: str

    @field_validator('manager_address')
    def validate_manager_address(cls, v: str) -> str:
        try:
            encoding.decode_address(v)
        except Exception as e:
            raise ValueError(f"Invalid manager address: {e}")
        return v

class CaSysYieldDistribution(BaseModel):
    """CaSys Yield Distribution Details"""
    timestamp: int
    total_amount: int
    distribution_rate: int
