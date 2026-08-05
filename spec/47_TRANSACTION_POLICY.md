# Transactions

One transaction per write use case.

Read operations are transaction-free.

Rollback on:

- validation failure
- persistence failure
- business rule violation

Nested transactions are forbidden in MVP.