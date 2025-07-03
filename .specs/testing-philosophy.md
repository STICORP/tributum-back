# Testing Philosophy for Tributum

This document outlines our testing philosophy and how it evolves as the system grows from infrastructure to a full financial application.

## Current Phase: Infrastructure Development

We are currently building the foundation - cross-cutting concerns, middleware, logging, configuration, and base repository patterns. In this phase, **heavy use of mocking is appropriate and follows best practices**.

### Why Mocking Makes Sense Now

1. **Testing Infrastructure Components**: When testing middleware, logging, error handlers, and configuration, we need to mock to verify specific behaviors. We're testing the "plumbing", not business logic.

2. **Framework-Level Testing**: Our tests verify technical specifications:
   - Logging middleware captures the correct fields
   - Error handlers transform exceptions properly
   - Configuration loads with proper validation
   - Repository base class provides expected methods

3. **Speed and Isolation**: For infrastructure code, fast feedback and parallel test execution are crucial. Mocking prevents cascading failures in foundation code.

### Current Testing Examples

**Infrastructure Test with Mocks (Appropriate)**:

```python
async def test_request_logging_middleware(mocker: MockerFixture) -> None:
    """Test that middleware logs requests correctly."""
    mock_logger = mocker.Mock()
    mocker.patch("src.api.middleware.request_logging.get_logger", return_value=mock_logger)

    # Test that specific fields are logged
    response = client.get("/test")

    # Verify technical contract
    mock_logger.info.assert_called_with(
        "request_started",
        method="GET",
        path="/test",
        correlation_id=ANY
    )
```

**Repository Test with Mocks (Appropriate for base class)**:

```python
async def test_base_repository_create(mock_session: MagicMock) -> None:
    """Test that base repository correctly implements create."""
    repo = BaseRepository(mock_session, TestModel)

    # Mock the database interaction
    mocker.patch.object(mock_session, "add")
    mocker.patch.object(mock_session, "flush", AsyncMock())

    result = await repo.create(instance)

    # Verify the technical contract
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
```

## Future Phase: Domain Implementation

When we start implementing business logic, our testing approach will evolve. **The infrastructure tests remain valid**, but we add new testing patterns for domain logic.

### Testing Pyramid for Financial Systems

```
Pure Unit Tests (40%):
├── Business logic (zero mocks)
├── Domain entities and value objects
├── Business rule validation
└── Calculations (tax, fees, interest)

Integration Tests (40%):
├── Repository tests with real database
├── API endpoint tests with real middleware
├── Service layer tests with dependencies
└── Transaction flows

Contract Tests (15%):
├── External API integrations
├── Database schema compatibility
└── Message queue contracts

E2E Tests (5%):
├── Critical user journeys
└── Complete payment flows
```

### Future Testing Examples

**Domain Logic Test (No Mocks)**:

```python
def test_tax_calculation():
    """Test tax calculation business logic."""
    calculator = TaxCalculator()

    result = calculator.calculate(
        amount=Decimal("1000.00"),
        tax_rate=Decimal("0.15"),
        tax_type=TaxType.INCOME
    )

    assert result.tax_amount == Decimal("150.00")
    assert result.total == Decimal("1150.00")
    assert result.breakdown.base_amount == Decimal("1000.00")
```

**Domain Entity Test (No Mocks)**:

```python
def test_payment_state_transitions():
    """Test payment entity state machine."""
    payment = Payment(
        amount=Decimal("100.00"),
        currency="USD",
        payer_id=123
    )

    # Test valid transition
    payment.authorize()
    assert payment.status == PaymentStatus.AUTHORIZED

    # Test invalid transition
    with pytest.raises(InvalidStateTransition):
        payment.refund()  # Can't refund non-captured payment
```

**Service Layer Test (Minimal Mocks)**:

```python
async def test_payment_service_with_real_components(db_session: AsyncSession):
    """Test payment service with real database."""
    # Use real repository with test database
    payment_repo = PaymentRepository(db_session)
    tax_calculator = TaxCalculator()  # Real calculator

    # Mock only external payment gateway
    gateway = MockPaymentGateway()

    service = PaymentService(
        repository=payment_repo,
        tax_calculator=tax_calculator,
        gateway=gateway
    )

    result = await service.process_payment(
        amount=Decimal("100.00"),
        payment_method="card"
    )

    # Verify in real database
    stored = await payment_repo.get_by_id(result.payment_id)
    assert stored.status == PaymentStatus.CAPTURED
```

**In-Memory Test Double (Alternative to Mocks)**:

```python
class InMemoryPaymentRepository(PaymentRepositoryInterface):
    """In-memory implementation for testing."""

    def __init__(self):
        self._payments: dict[int, Payment] = {}
        self._next_id = 1

    async def create(self, payment: Payment) -> Payment:
        payment.id = self._next_id
        self._payments[self._next_id] = payment
        self._next_id += 1
        return payment

    async def get_by_id(self, payment_id: int) -> Payment | None:
        return self._payments.get(payment_id)
```

## Testing Guidelines

### When to Use Mocks

✅ **Use mocks for**:

- External services (payment gateways, tax APIs)
- Infrastructure behavior verification
- Error simulation
- Time-dependent operations

❌ **Don't mock**:

- Business logic
- Domain entities
- Value objects
- In-memory operations

### Mock at the Right Boundary

```python
# ❌ Bad: Mocking too deep
mocker.patch.object(calculator, "_apply_tax_rate")
mocker.patch.object(calculator, "_round_amount")

# ✅ Good: Mock at service boundary
mocker.patch.object(external_tax_service, "get_current_rates")
```

### Test Behavior, Not Implementation

```python
# ❌ Bad: Testing implementation details
def test_logger_called_three_times():
    # Process payment
    assert mock_logger.info.call_count == 3

# ✅ Good: Testing behavior
def test_payment_creates_audit_trail():
    # Process payment
    audit_entries = await audit_repo.get_by_payment(payment.id)
    assert len(audit_entries) == 3
    assert audit_entries[0].action == "PAYMENT_INITIATED"
```

## Migration Strategy

### Phase 1: Current State (Infrastructure Only)

- Continue with mock-heavy tests for infrastructure
- Maintain high coverage for technical components
- Keep integration tests for database operations

### Phase 2: Early Domain Implementation

- Start with pure domain logic (no infrastructure dependencies)
- Write tests with zero mocks for business rules
- Create interfaces for repositories

### Phase 3: Service Layer Development

- Use in-memory implementations for repositories in tests
- Mock only external services
- Add integration tests with real database

### Phase 4: Full System

- Maintain infrastructure tests as-is
- Balance testing pyramid (40% unit, 40% integration)
- Add contract tests for external integrations
- Minimal E2E tests for critical paths

## Financial System Considerations

For a payment/tax system, prioritize:

1. **Correctness over speed**: Use real components where possible
2. **Audit trail testing**: Ensure all financial operations are traceable
3. **Edge case coverage**: Test boundary conditions extensively
4. **Precision testing**: Verify decimal calculations exactly
5. **Concurrency testing**: Test race conditions in payment processing

## Examples of What to Test at Each Layer

### Infrastructure Layer (Current)

- Middleware behavior
- Logging output format
- Error transformation
- Configuration validation
- Database connection pooling

### Domain Layer (Future)

- Tax calculations
- Payment state machines
- Business rule validation
- Entity invariants
- Value object equality

### Application Layer (Future)

- Service orchestration
- Transaction boundaries
- Event publishing
- Workflow completion

### API Layer

- Request validation
- Response formatting
- Authentication/authorization
- Rate limiting
- API versioning

## Conclusion

Our current mock-heavy approach is appropriate for infrastructure development. As we implement domain logic, we'll naturally evolve to a more balanced testing strategy that provides high confidence in our financial calculations and business rules while maintaining fast, reliable tests.

Remember: **The goal is confidence in correctness**, especially for financial systems. Choose the testing approach that best achieves this for each component.
