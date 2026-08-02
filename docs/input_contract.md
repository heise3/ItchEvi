# Input contract summary

The qualification core consumes four versioned inputs:

1. Evidence records: one entity-layer terminal record with provenance.
2. Entities: prespecified claims and construction layer.
3. Layers: critical, required, or optional evidence definitions and weights.
4. Qualification configuration: coverage, support, conflict, discovery, and
   stability gates.

Blank numeric TSV fields represent missing values. `itchevi normalize`
converts these fields to JSON `null`. Unknown columns are rejected to prevent
silent information loss. Every input change requires a new content hash.
