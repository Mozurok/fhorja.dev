# Column alignment rules

| Cell content        | Alignment | Padding character |
| ------------------- | --------- | ----------------- |
| Text                | left      | space             |
| Integer             | right     | space             |
| Decimal             | right     | space             |
| Date (ISO 8601)     | left      | space             |
| Empty               | left      | space             |

A header separator row keeps the colons it already had. A column with no colons
is treated as left aligned.
