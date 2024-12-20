# CaSys Token System

A decentralized finance (DeFi) platform built on Algorand, implementing a token system with bonds, collateral management, and governance features.

## Features

- Fixed supply token with governance-controlled minting
- Bond system with collateral backing
- Decentralized governance (DAO)
- Yield distribution system
- Automated collateral management

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/casys-token.git
cd casys-token

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Token Management
```python
from contracts.token.casys_token_manager import CaSysTokenManager
from contracts.models import CaSysTokenConfig

# Create token manager
token_manager = CaSysTokenManager(algod_client)

# Configure token
config = CaSysTokenConfig(
    total_supply=1000000,
    manager=creator_address
)

# Create token
token_id = token_manager.create_token(creator_private_key, config)
```

### 2. Bond Creation
```python
from contracts.bonds.casys_bond_manager import CaSysBondManager
from contracts.models import CaSysBondConfig

# Create bond
bond = bond_manager.create_bond(app_id, investor_private_key, amount)
```

### 3. Governance
```python
from contracts.governance.casys_dao_manager import CaSysDAOManager

# Create proposal
proposal = dao_manager.create_proposal(
    app_id,
    creator_private_key,
    "Title",
    "Description",
    execution_delay
)
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_integration.py

# Run with coverage
pytest --cov=contracts tests/
```

### Documentation
- [Architecture](docs/ARCHITECTURE.md)
- [Specifications](docs/SPECIFICATIONS.md)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
