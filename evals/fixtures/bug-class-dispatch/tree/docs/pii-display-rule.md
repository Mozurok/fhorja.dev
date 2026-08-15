# Sensitive identifier display rule

Any surface that shows a card number, bank account number, routing number, or
tax id shows exactly the last four digits and nothing more. That covers rendered
screens, API responses, log lines, analytics events, and webhook payloads. There
is no side-channel exemption and no internal-tool exemption.

Masking happens on the server, before serialization. A value truncated in the
browser has already crossed the boundary and counts as exposed.

The single implementation is `last4()` in
`packages/api-contracts/serializers/base.ts`. Nothing re-implements it.
