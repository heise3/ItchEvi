# Input contract summary

The qualification core consumes four versioned inputs:

1. Evidence records: one entity-layer terminal record with provenance.
2. Entities: prespecified claims and construction layer.
3. Layers: critical, required, or optional evidence definitions and weights.
4. Qualification configuration: coverage, support, conflict, discovery, and
   stability gates plus outcome-independent boolean condition flags.

Blank numeric TSV fields represent missing values. `itchevi normalize`
converts these fields to JSON `null`. Unknown columns are rejected to prevent
silent information loss. Every evidence record requires nonblank input and
configuration SHA256 values. Every input change requires a new content hash.

Construction layers must be `critical` or `required`. The minimum independent
unit threshold applies to every active required layer. Conditional required
layers use `flag:<name>` and a matching boolean in `condition_flags`; a false
flag produces an explicit not-applicable receipt and removes that layer from
the active qualification denominator.
